import json

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.db.models import F, Q, IntegerField, Count
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.utils.html import strip_tags
from django.utils import timezone
from projects.models import Project
from allocations.models import Allocation
from rest_framework.renderers import JSONRenderer
from rest_framework import serializers
from util.project_allocation_mapper import ProjectAllocationMapper
from util.keycloak_client import KeycloakClient

from .forms import (
    ArtifactForm,
    ArtifactVersionForm,
    AuthorFormset,
    ShareArtifactForm,
    ZenodoPublishFormset,
    RequestDayPassForm,
    ReviewDayPassForm,
)
from .models import Artifact, ArtifactVersion, Author, ShareTarget, DayPassRequest
from .tasks import publish_to_zenodo
from projects.views import (
    add_project_invitation,
    get_invite_url,
    get_project_membership_managers,
    is_membership_manager,
    manage_membership_in_scope,
)

import logging

LOG = logging.getLogger(__name__)

SHARING_KEY_PARAM = "s"


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = "__all__"


def can_edit(request, artifact):
    if artifact.created_by == request.user:
        return True
    if request.user.is_staff:
        return True
    return False


def check_edit_permission(func):
    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop('pk')
        artifact = get_object_or_404(Artifact, pk=pk)
        if not can_edit(request, artifact):
            messages.add_message(request, messages.ERROR,
                'You do not have permission to edit this artifact.')
            return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))
        # Replace pk with Artifact instance to avoid another lookup
        kwargs.setdefault('artifact', artifact)
        return func(request, *args, **kwargs)
    return wrapper


def check_view_permission(func):
    def can_view(request, artifact):
        if artifact.deleted:
            return []

        all_versions = list(artifact.versions)

        if artifact.is_public:
            return all_versions

        if artifact.sharing_key and (
            request.GET.get(SHARING_KEY_PARAM) == artifact.sharing_key
        ):
            return all_versions

        if request.user.is_authenticated:
            if request.user.is_staff:
                return all_versions
            if artifact.created_by == request.user:
                return all_versions
            project_shares = ShareTarget.objects.filter(
                artifact=artifact, project__isnull=False)
            # Avoid the membership lookup if there are no sharing rules in place
            if project_shares:
                mapper = ProjectAllocationMapper(request)
                user_projects = [
                    p["chargeCode"]
                    for p in mapper.get_user_projects(
                        request.user.username, fetch_balance=False
                    )
                ]
                if any(p.project.charge_code in user_projects for p in project_shares):
                    return all_versions

        # NOTE(jason): It is important that this check go last. Visibility b/c
        # the artifact has a DOI is the weakest form of visibility; not all
        # versions are necessarily visible in this case. We return a list of
        # the versions that are allowed. We check for stronger visibilty rules
        # first, as they should ensure all versions are seen.
        if artifact.doi:
            return [v for v in all_versions if v.doi]

        return []

    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop('pk')
        artifact = get_object_or_404(Artifact, pk=pk)
        artifact_versions = can_view(request, artifact)
        if not artifact_versions:
            raise Http404('The requested artifact does not exist, or you do not have permission to view.')
        # Replace pk with Artifact instance to avoid another lookup
        kwargs.setdefault('artifact', artifact)
        kwargs.setdefault('artifact_versions', artifact_versions)
        return func(request, *args, **kwargs)
    return wrapper


class ArtifactFilter:
    @staticmethod
    def MINE(request):
        if request.user.is_authenticated:
            return Q(created_by=request.user)
        else:
            return Q()

    PUBLIC = Q(is_public=True) | (
        Q(doi__isnull=False)
        & Q(artifact_versions__deposition_repo=ArtifactVersion.ZENODO)
    )

    @staticmethod
    def PROJECT(projects):
        return Q(shared_to_projects__in=projects)


def _render_list(request, artifacts, user_projects=None):
    if not user_projects:
        if request.user.is_authenticated:
            mapper = ProjectAllocationMapper(request)
            user_projects = mapper.get_user_projects(
                request.user.username, fetch_balance=False
            )
        else:
            user_projects = []

    template = loader.get_template('sharing_portal/index.html')
    context = {
        'hub_url': settings.ARTIFACT_SHARING_JUPYTERHUB_URL,
        'artifacts': artifacts.order_by('-created_at'),
        'projects': user_projects,
    }

    return HttpResponse(template.render(context, request))


def index_all(request, collection=None):
    user_projects = None
    if request.user.is_authenticated:
        mapper = ProjectAllocationMapper(request)
        user_projects = mapper.get_user_projects(
            request.user.username, fetch_balance=False)
        charge_codes = [p['chargeCode'] for p in user_projects]
        projects = Project.objects.filter(charge_code__in=charge_codes)
        f = (ArtifactFilter.MINE(request) | ArtifactFilter.PROJECT(projects) | ArtifactFilter.PUBLIC)
    else:
        f = ArtifactFilter.PUBLIC

    artifacts = _fetch_artifacts(f)
    # Pass user_projects to list to avoid a second fetch of this data
    return _render_list(request, artifacts, user_projects=user_projects)


@login_required
def index_mine(request):
    artifacts = _fetch_artifacts(ArtifactFilter.MINE(request))
    return _render_list(request, artifacts)


def index_public(request):
    artifacts = _fetch_artifacts(ArtifactFilter.PUBLIC)
    return _render_list(request, artifacts)


def index_project(request, charge_code):
    projects = Project.objects.filter(charge_code=charge_code)
    artifacts = _fetch_artifacts(ArtifactFilter.PROJECT(projects))
    return _render_list(request, artifacts)


def _fetch_artifacts(filters):
    """Fetch all artifacts matching a given set of filters.

    This uses a few advanced Django ORM mechanisms. We use `prefetch_related`
    to allow us to perform filtering at the artifact version level. We do this
    so we can hide non-public versions of public artifacts, when viewed w/o
    any special access permissions. The query also includes a count aggregator
    to act over the artifact versions collection; this is used to render stats
    in some places.
    """
    return (
        Artifact.objects.prefetch_related("artifact_versions")
        .filter(filters)
        .filter(deleted=False)
        .annotate(num_versions=Count("artifact_versions"))
    )


@check_edit_permission
@login_required
def edit_artifact(request, artifact):
    if request.method == "POST":
        form = ArtifactForm(request.POST, instance=artifact, request=request)

        if "delete_version" in request.POST:
            version_id = request.POST.get("delete_version")
            try:
                version = artifact.versions.get(pk=version_id)
                if not version.doi:
                    version.delete()
                    messages.add_message(request, messages.SUCCESS,
                        'Successfully deleted artifact version.')
                else:
                    messages.add_message(request, messages.ERROR,
                        'Cannot delete versions already assigned a DOI.')
            except ArtifactVersion.DoesNotExist:
                messages.add_message(request, messages.ERROR,
                    'Artifact version {} does not exist'.format(version_id))
            # Return to edit form
            return HttpResponseRedirect(
                reverse('sharing_portal:edit', args=[artifact.pk]))

        artifact, errors = _handle_artifact_forms(request, form)
        if errors:
            (messages.add_message(request, messages.ERROR, e) for e in errors)
        else:
            messages.add_message(request, messages.SUCCESS, 'Successfully saved artifact.')
        return HttpResponseRedirect(
            reverse("sharing_portal:detail", args=[artifact.pk])
        )

    form = ArtifactForm(instance=artifact, request=request)
    template = loader.get_template("sharing_portal/edit.html")
    context = {
        'artifact_form': form,
        'artifact': artifact,
        'all_versions': _artifact_display_versions(artifact.versions),
    }

    return HttpResponse(template.render(context, request))


@check_edit_permission
@login_required
def share_artifact(request, artifact):
    if request.method == 'POST':

        form = ShareArtifactForm(
            request,
            request.POST
        )
        z_form = ZenodoPublishFormset(request.POST, artifact_versions=artifact.versions)

        form = ShareArtifactForm(request, request.POST)
        if form.is_valid():
            artifact.is_public = form.cleaned_data["is_public"]
            artifact.is_reproducible = form.cleaned_data["is_reproducible"]
            artifact.reproduce_hours = form.cleaned_data["reproduce_hours"]
            try:
                artifact.project = Project.objects.get(
                    charge_code=form.cleaned_data["project"]
                )
            except Project.DoesNotExist:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Project {} does not exist".format(form.cleaned_data["project"]),
                )
                return HttpResponseRedirect(
                    reverse("sharing_portal:share", args=[artifact.pk])
                )

            if artifact.is_reproducible and not artifact.reproducibility_project:
                supplemental_project = create_supplemental_project(request, artifact)
                artifact.reproducibility_project = supplemental_project
            artifact.save()
            if (_sync_share_targets(artifact, project_shares=form.cleaned_data['projects'])):
                messages.add_message(request, messages.SUCCESS,
                    'Successfully updated sharing settings')

            if (z_form.is_valid() and
                _request_artifact_dois(artifact, request_forms=z_form.cleaned_data)):
                messages.add_message(request, messages.SUCCESS,
                    ('Requested DOI(s) for artifact versions. The process '
                     'of issuing DOIs may take a few minutes.'))

            return HttpResponseRedirect(reverse('sharing_portal:detail', args=[artifact.pk]))
    else:
        form = ShareArtifactForm(
            request,
            initial={
                "is_public": artifact.is_public,
                "projects": artifact.shared_to_projects.all(),
                "is_reproducible": artifact.is_reproducible,
                "project": artifact.project,
                "reproduce_hours": artifact.reproduce_hours,
            },
        )
        z_form = ZenodoPublishFormset(artifact_versions=artifact.versions)

    share_url = request.build_absolute_uri(
        reverse("sharing_portal:detail", kwargs={"pk": artifact.pk})
    )
    if artifact.sharing_key:
        share_url += "?{key_name}={key_value}".format(
            key_name=SHARING_KEY_PARAM, key_value=artifact.sharing_key
        )

    template = loader.get_template("sharing_portal/share.html")
    context = {
        "share_form": form,
        "z_management_form": z_form.management_form,
        "z_forms": _artifact_display_versions(z_form.forms),
        "share_url": share_url,
        "artifact": artifact,
        "artifact_json": JSONRenderer().render(
            ArtifactSerializer(instance=artifact).data
        ),
    }
    return HttpResponse(template.render(context, request))


def has_active_allocations(request):
    mapper = ProjectAllocationMapper(request)
    user_projects = mapper.get_user_projects(
        request.user.username, to_pytas_model=False
    )
    for project in user_projects:
        for allocation in project["allocations"]:
            if allocation["status"].lower() == "active":
                return True
    return False


def preserve_sharing_key(url, request):
    if SHARING_KEY_PARAM in request.GET:
        return url + "?{}={}".format(SHARING_KEY_PARAM, request.GET[SHARING_KEY_PARAM])
    return url


@check_view_permission
def artifact(request, artifact, artifact_versions, version_idx=None):
    show_launch = request.user is None or has_active_allocations(request)

    version = _artifact_version(artifact_versions, version_idx)
    if not version:
        error_message = "This artifact has no version {}".format(version_idx)
        messages.add_message(request, messages.ERROR, error_message)

    if version_idx:
        launch_url = reverse('sharing_portal:launch_version',
            args=[artifact.pk, version_idx])
        doi_info = {
            'doi': version.doi,
            'url': version.deposition_url,
            'created_at': version.created_at,
        }
    else:
        launch_url = reverse('sharing_portal:launch', args=[artifact.pk])
        doi_info = {
            'doi': artifact.doi,
            'url': artifact.deposition_url,
            'created_at': None,
        }

    # Ensure launch URLs are authenticated if a private link is being used.
    request_day_pass_url = preserve_sharing_key(
        reverse("sharing_portal:request_day_pass", args=[artifact.pk]), request
    )
    launch_url = preserve_sharing_key(launch_url, request)

    template = loader.get_template("sharing_portal/detail.html")

    context = {
        "artifact": artifact,
        "all_versions": _artifact_display_versions(artifact_versions),
        "doi_info": doi_info,
        "version": version,
        "launch_url": launch_url,
        "related_artifacts": artifact.related_items,
        "request_day_pass_url": request_day_pass_url,
        "editable": (request.user.is_staff or (artifact.created_by == request.user)),
        "show_launch": show_launch,
    }
    template = loader.get_template("sharing_portal/detail.html")
    return HttpResponse(template.render(context, request))


@check_view_permission
@login_required
def launch(request, artifact, artifact_versions, version_idx=None):
    version = _artifact_version(artifact_versions, version_idx)

    if not version:
        raise Http404((
            'There is no version {} for this artifact, or you do not have access.'
            .format(version_idx or '')))

    # If no allocation, redirerect to request day pass
    if artifact.is_reproducible and not has_active_allocations(request):
        day_pass_request_url = preserve_sharing_key(
            reverse("sharing_portal:request_day_pass", args=[artifact.pk]), request
        )
        return redirect(day_pass_request_url)

    version.launch_count = F("launch_count") + 1
    version.save(update_fields=["launch_count"])
    return redirect(version.launch_url(can_edit=can_edit(request, artifact)))


@check_view_permission
@login_required
def request_day_pass(request, artifact, **kwargs):
    if not artifact or not artifact.is_reproducible:
        raise Http404("That artifact either doesn't exist, or can't be reproduced")

    if request.method == "POST":
        form = RequestDayPassForm(
            request.POST,
            request,
        )
        if form.is_valid():
            day_pass_request = DayPassRequest.objects.create(
                artifact=artifact,
                name=form.cleaned_data["name"],
                institution=form.cleaned_data["institution"],
                reason=form.cleaned_data["reason"],
                created_by=request.user,
                status=DayPassRequest.STATUS_PENDING,
            )
            send_request_mail(day_pass_request, request)

            messages.add_message(request, messages.SUCCESS, "Request submitted")
            return HttpResponseRedirect(
                preserve_sharing_key(
                    reverse("sharing_portal:detail", args=[artifact.pk]), request
                )
            )
        else:
            if form.errors:
                (messages.add_message(request, messages.ERROR, e) for e in form.errors)
            return HttpResponseRedirect(
                preserve_sharing_key(
                    reverse("sharing_portal:request_day_pass", args=[artifact.pk]),
                    request,
                )
            )

    form = RequestDayPassForm(
        initial={
            "name": f"{request.user.first_name} {request.user.last_name}",
            "email": request.user.email,
        }
    )

    template = loader.get_template("sharing_portal/request_day_pass.html")
    context = {
        "artifact": artifact,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def send_request_mail(day_pass_request, request):
    url = request.build_absolute_uri(
        reverse("sharing_portal:review_day_pass", args=[day_pass_request.id])
    )
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    list_url = request.build_absolute_uri(
        reverse("sharing_portal:list_day_pass_requests")
    )
    subject = f'Day pass request for "{day_pass_request.artifact.title}"'
    body = f"""
    <p>
    A request has been made to reproduce the artifact:
    {day_pass_request.artifact.title}.
    </p>
    <p>
    Review this decision by visiting <a href="{url}">this link</a>,
    or by going to {url} in your browser. You can view all pending and reviewed
    requests <a href="{list_url}">here</a> or at {list_url}.
    </p>
    <p><i>This is an automatic email, please <b>DO NOT</b> reply!
    If you have any question or issue, please submit a ticket on our
    <a href="{help_url}">help desk</a>.
    </i></p>
    <p>Thanks,</p>
    <p>Chameleon Team</p>
    """
    managers = [
        u.email
        for u in get_project_membership_managers(day_pass_request.artifact.project)
    ]
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=managers,
        message=strip_tags(body),
        html_message=body,
    )


@login_required
def review_day_pass(request, request_id, **kwargs):
    try:
        day_pass_request = DayPassRequest.objects.get(pk=request_id)
    except DayPassRequest.DoesNotExist:
        raise Http404("That day pass request does not exist")

    if not day_pass_request.artifact.project or not is_membership_manager(
        day_pass_request.artifact.project, request.user.username
    ):
        raise PermissionDenied("You do not have permission to view that page")

    if day_pass_request.status != DayPassRequest.STATUS_PENDING:
        messages.add_message(
            request,
            messages.SUCCESS,
            f"This request was already reviewed by: {day_pass_request.decision_by.username}",
        )
        return HttpResponseRedirect(reverse("sharing_portal:list_day_pass_requests"))

    if request.method == "POST":
        form = ReviewDayPassForm(
            request.POST,
            request,
        )
        if form.is_valid():
            status = form.cleaned_data["status"]
            day_pass_request.status = status
            day_pass_request.decision_at = timezone.now()
            day_pass_request.decision_by = request.user
            day_pass_request.save()
            send_request_decision_mail(day_pass_request, request)
            messages.add_message(request, messages.SUCCESS, f"Request status: {status}")
            return HttpResponseRedirect(
                reverse("sharing_portal:detail", args=[day_pass_request.artifact.pk])
            )
        else:
            if form.errors:
                (messages.add_message(request, messages.ERROR, e) for e in form.errors)
            return HttpResponseRedirect(
                reverse("sharing_portal:review_day_pass", args=[request_id])
            )

    form = ReviewDayPassForm()

    template = loader.get_template("sharing_portal/review_day_pass.html")
    context = {
        "day_pass_request": day_pass_request,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


@login_required
def list_day_pass_requests(request, **kwargs):
    keycloak_client = KeycloakClient()
    projects = [
        project["groupName"]
        for project in keycloak_client.get_user_roles(request.user.username)
        if manage_membership_in_scope(project["scopes"])
    ]
    pending_requests = (
        DayPassRequest.objects.all()
        .filter(
            artifact__project__charge_code__in=projects,
            status=DayPassRequest.STATUS_PENDING,
        )
        .order_by("-created_at")
    )
    for day_pass_request in pending_requests:
        day_pass_request.url = reverse(
            "sharing_portal:review_day_pass", args=[day_pass_request.id]
        )
    reviewed_requests = (
        DayPassRequest.objects.all()
        .exclude(status=DayPassRequest.STATUS_PENDING)
        .filter(artifact__project__charge_code__in=projects)
        .order_by("-created_at")
    )
    template = loader.get_template("sharing_portal/list_day_pass_requests.html")
    context = {
        "pending_requests": pending_requests,
        "reviewed_requests": reviewed_requests,
    }
    return HttpResponse(template.render(context, request))


def send_request_decision_mail(day_pass_request, request):
    subject = f"Day pass request has been reviewed: {day_pass_request.status}"
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    if day_pass_request.status == DayPassRequest.STATUS_APPROVED:
        invite = add_project_invitation(
            day_pass_request.artifact.reproducibility_project.id,
            day_pass_request.created_by.email,
            day_pass_request.decision_by,
            request.get_host(),
            day_pass_request.artifact.reproduce_hours,
            False,
        )
        day_pass_request.invitation = invite
        day_pass_request.save()
        url = get_invite_url(request, invite.email_code)
        artifact_url = request.build_absolute_uri(
            reverse("sharing_portal:detail", args=[day_pass_request.artifact.id])
        )
        body = f"""
        <p>
        Your day pass request to reproduce {day_pass_request.artifact.title}
        has been approved. Your access will be for {invite.duration} hours,
        and begins when you click <a href="{url}">this link</a>,
        or by going to {url} in your browser.
        </p>
        <p>
        After accepting the invitation, you can navigate back to the artifact
        at {artifact_url}. Please use the project
        {day_pass_request.artifact.reproducibility_project.charge_code} when
        running your experiment.
        </p>
        <p><i>This is an automatic email, please <b>DO NOT</b> reply!
        If you have any question or issue, please submit a ticket on our
        <a href="{help_url}">help desk</a>.
        </i></p>
        <p>Thanks,</p>
        <p>Chameleon Team</p>
        """
    elif day_pass_request.status == DayPassRequest.STATUS_REJECTED:
        body = f"""
        <p>
        Your day pass request to reproduce '{day_pass_request.artifact.title}'
        has been rejected.
        </p>
        <p><i>This is an automatic email, please <b>DO NOT</b> reply!
        If you have any question or issue, please submit a ticket on our
        <a href="{help_url}">help desk</a>.
        </i></p>
        <p>Thanks,</p>
        <p>Chameleon Team</p>
        """
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[day_pass_request.created_by.email],
        message=strip_tags(body),
        html_message=body,
    )


def _artifact_version(artifact_versions, version_idx=None):
    # A default of 0 means get the most recent artifact version.
    # Version indices are 1-indexed.
    version_idx = version_idx or 0
    try:
        return artifact_versions[int(version_idx) - 1]
    except (IndexError, ValueError):
        return None


@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
@login_required
def embed_create(request):
    return _embed_form(request, context={'form_title': 'Create artifact'})


@check_edit_permission
@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
@login_required
def embed_edit(request, artifact):
    context = {}
    if 'new_version' in request.GET:
        context['form_title'] = 'Create new version of artifact'
    else:
        context['form_title'] = 'Edit artifact'

    return _embed_form(request, artifact=artifact, context=context)


@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
def embed_cancel(request):
    return _embed_callback(request, dict(status='cancel'))


def _embed_form(request, artifact=None, context={}):
    new_version = (not artifact) or ("new_version" in request.GET)

    if request.method == "POST":
        form = ArtifactForm(request.POST, instance=artifact, request=request)
        authors_formset = AuthorFormset(request.POST)
        if (not artifact) or new_version:
            version_form = ArtifactVersionForm(request.POST)
        else:
            version_form = None

        artifact, errors = _handle_artifact_forms(request, form,
            authors_formset=authors_formset, version_form=version_form)

        if not errors:
            return _embed_callback(request, dict(status='success', id=artifact.pk))
        else:
            # Fail through and return to form with errors displayed
            for err in errors:
                messages.add_message(request, messages.ERROR, err)
    else:
        form = ArtifactForm(instance=artifact, request=request)
        if artifact:
            queryset = artifact.authors.all()
            initial = None
        else:
            queryset = Author.objects.none()
            # Default to logged-in user
            initial = [{'name': request.user.get_full_name()}]
        authors_formset = AuthorFormset(queryset=queryset, initial=initial)
        if new_version:
            version_form = ArtifactVersionForm(
                initial={
                    'deposition_id': request.GET.get('deposition_id'),
                    'deposition_repo': request.GET.get('deposition_repo')
                })
        else:
            version_form = None

    template = loader.get_template('sharing_portal/embed.html')
    context.update({
        'artifact_form': form,
        'authors_formset': authors_formset,
        'version_form': version_form,
    })

    return HttpResponse(template.render(context, request))

def _embed_callback(request, payload):
    template = loader.get_template('sharing_portal/embed_callback.html')
    payload_wrapper = dict(
        message='save_result',
        body=payload,
    )
    context = {
        'payload_json': json.dumps(payload_wrapper),
        'jupyterhub_origin': settings.ARTIFACT_SHARING_JUPYTERHUB_URL,
    }

    return HttpResponse(template.render(context, request))


def _handle_artifact_forms(request, artifact_form, authors_formset=None,
                           version_form=None):
    artifact = None
    errors = []

    if artifact_form.is_valid():
        artifact = artifact_form.save(commit=False)
        authors = None
        version = None

        if authors_formset:
            if authors_formset.is_valid():
                # Save the list of authors. First we save the new authors items
                # (users may have added new authors). Then we get the list of
                # all author models in the formset and replace the 'authors'
                # m2m list of the artifact. There are probably less ugly ways
                # of doing this, but this is a weird form.
                authors_formset.save()
                authors = [
                    f.instance for f in authors_formset.forms
                    if f.instance.pk is not None and
                    (f.instance not in authors_formset.deleted_objects)
                ]
            else:
                errors.extend(authors_formset.errors)

        if version_form:
            if version_form.is_valid():
                version = version_form.save(commit=False)
                # Remove the version form to prevent re-submit
                version_form = None
            else:
                errors.extend(version_form.errors)

        if not errors:
            if not artifact.pk:
                artifact.created_by = request.user
            artifact.updated_by = request.user
            artifact.save()
            if authors:
                artifact.authors.set(authors)
            if version:
                version.artifact = artifact
                version.save()
            # Save the labels
            artifact_form.save_m2m()
    else:
        errors.extend(artifact_form.errors)

    return artifact, errors


def _artifact_display_versions(versions):
    """Return a list of artifact versions for display purposes.

    This is slightly different than the 'versions' property of the artifact, as
    it is reverse-sorted (newest at the top) and also enumerated so that while
    it's reversed, the numbers still indicate chronological order.
    """
    versions_list = list(versions)
    return [
        (len(versions) - i, v)
        for (i, v) in enumerate(reversed(versions_list))
    ]


def _sync_share_targets(artifact, project_shares=[]):
    existing_targets = ShareTarget.objects.filter(artifact=artifact)
    existing_project_shares = [st.project for st in existing_targets if st.project]
    incoming_project_shares = project_shares
    changed = False
    for p in existing_project_shares:
        if p not in incoming_project_shares:
            (ShareTarget.objects.filter(artifact=artifact, project=p)
                .delete())
            LOG.info('Un-shared artifact %s to project %s', artifact.pk, p.pk)
            changed = True
    for p in incoming_project_shares:
        if p not in existing_project_shares:
            ShareTarget.objects.create(artifact=artifact, project=p)
            LOG.info('Shared artifact %s to project %s', artifact.pk, p.pk)
            changed = True
    return changed


def _request_artifact_dois(artifact, request_forms=[]):
    """Process Zenodo artifact DOI request forms.

    Returns:
        bool: if any DOIs were requested.
    """
    try:
        to_request = [
            f['artifact_version_id']
            for f in request_forms if f['request_doi']
        ]
        if to_request:
            for artifact_version_id in to_request:
                publish_to_zenodo.apply_async(args=[artifact_version_id])
            return True
        return False
    except Exception:
        LOG.exception("Failed to request DOI for artifact {}".format(artifact.pk))


def create_supplemental_project(request, artifact):
    mapper = ProjectAllocationMapper(request)

    pi = artifact.project.pi
    artifact_url = request.build_absolute_uri(
        reverse("sharing_portal:detail", kwargs={"pk": artifact.pk})
    )
    supplemental_project = {
        "nickname": f"reproducing_{artifact.id}",
        "title": f"Reproducing '{artifact.title}'",
        "description": f"This project is for reproducing the artifact '{artifact.title}' {artifact_url}",
        "typeId": artifact.project.type.id,
        "fieldId": artifact.project.field.id,
        "piId": artifact.project.pi.id,
    }
    # Approval code is commented out during initial preview release.
    allocation_data = {
        "resourceId": 39,
        "requestorId": pi.id,
        "computeRequested": 1000,
        "status": "approved",
        #"dateReviewed": timezone.now(),
        #"start": timezone.now(),
        #"end": timezone.now() + timedelta(days=6*30),
        #"decisionSummary": "automatically approved for reproducibility",
        #"computeAllocated": 1000,
        #"justification": "Automatic decision",
    }
    supplemental_project["allocations"] = [allocation_data]
    supplemental_project["source"] = "Day pass"
    created_tas_project = mapper.save_project(supplemental_project, request.get_host())
    # We can assume only 1 here since this project is new
    #allocation = Allocation.objects.get(project_id=created_tas_project["id"])
    #allocation.status = "approved"
    #allocation.save()
    return Project.objects.get(id=created_tas_project["id"])
