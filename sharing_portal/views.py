from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template import loader
from django.utils.html import strip_tags
from django.utils import timezone
from projects.models import Project
from projects.util import get_project_members
from util.project_allocation_mapper import ProjectAllocationMapper
from util.keycloak_client import KeycloakClient

from .forms import (
    ArtifactForm,
    AuthorFormset,
    AuthorCreateFormset,
    ShareArtifactForm,
    ZenodoPublishFormset,
    RequestDaypassForm,
    ReviewDaypassForm,
)
from .models import Artifact, DaypassRequest, DaypassProject
from . import trovi
from projects.views import (
    add_project_invitation,
    get_invite_url,
    get_project_membership_managers,
    is_membership_manager,
    manage_membership_in_scope,
)
from .zenodo import ZenodoClient

from urllib.parse import urlencode

import logging
from datetime import datetime, timedelta
import subprocess

LOG = logging.getLogger(__name__)

SHARING_KEY_PARAM = "s"


def with_trovi_token(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if (
            request.session.get("trovi_token_expiration")
            and datetime.utcnow().timestamp()
            > request.session["trovi_token_expiration"]
        ):
            request.session.pop("trovi_token_expiration", None)
            request.session.pop("trovi_token", None)

        if not request.session.get("trovi_token"):
            if request.session.get("oidc_access_token"):
                try:
                    response = trovi.get_token(
                        request.session.get("oidc_access_token"),
                        is_admin=False,
                    )
                    request.session["trovi_token"] = response["access_token"]
                    request.session["trovi_token_expiration"] = (
                        datetime.utcnow()
                        + timedelta(seconds=int(response["expires_in"]) - 10)
                    ).timestamp()
                except trovi.TroviException:
                    LOG.error("Error getting trovi token")
            else:
                # Set an empty token
                request.session["trovi_token"] = ""
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def can_edit(request, artifact):
    return _owns_artifact(request.user, artifact)


def handle_get_artifact(request, uuid, sharing_key=None):
    try:
        return trovi.get_artifact_by_trovi_uuid(
            request.session.get("trovi_token"), uuid, sharing_key=sharing_key
        )
    except trovi.TroviException as e:
        if e.code == 404:
            raise Http404("That artifact does not exist, or is private")
        if e.code == 403:
            raise PermissionDenied("You do not have permission to view that page")
        raise


def check_edit_permission(func):
    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop("pk")
        artifact = handle_get_artifact(request, pk)
        if not can_edit(request, artifact):
            messages.add_message(
                request,
                messages.ERROR,
                "You do not have permission to edit this artifact.",
            )
            return HttpResponseRedirect(reverse("sharing_portal:detail", args=[pk]))
        kwargs.setdefault("artifact", artifact)
        return func(request, *args, **kwargs)

    return wrapper


def get_artifact(func):
    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop("pk")
        sharing_key = request.GET.get(SHARING_KEY_PARAM, None)
        # If someone supplied an old PK (try to redirect)
        if len(pk) < 3:
            try:
                artifact = Artifact.objects.get(pk=pk)
                base = reverse("sharing_portal:detail", args=[artifact.trovi_uuid])
                query = {}
                if sharing_key:
                    query[SHARING_KEY_PARAM] = sharing_key
                return HttpResponseRedirect(f"{base}?{urlencode(query)}")
            except Artifact.DoesNotExist:
                # will raise 404 in normal handling
                pass
        artifact = handle_get_artifact(request, pk, sharing_key=sharing_key)
        kwargs.setdefault("artifact", artifact)
        return func(request, *args, **kwargs)

    return wrapper


def _render_list(request, artifacts):
    template = loader.get_template("sharing_portal/index.html")
    context = {
        "hub_url": settings.ARTIFACT_SHARING_JUPYTERHUB_URL,
        "artifacts": artifacts,
    }

    return HttpResponse(template.render(context, request))


def _compute_artifact_fields(artifact):
    terms = artifact["title"].lower().split()
    terms.extend([f"tag:{label.lower()}" for label in artifact["tags"]])
    for name in [author["full_name"] for author in artifact["authors"]]:
        terms.extend(name.lower().split(" "))
    artifact["search_terms"] = terms
    artifact["is_chameleon_supported"] = any(
        label == "chameleon" for label in artifact["tags"]
    )
    artifact["is_private"] = artifact["visibility"] == "private" and not _parse_doi(
        artifact
    )
    return artifact


def _owns_artifact(user, artifact):
    owner_urn = trovi.parse_owner_urn(artifact["owner_urn"])
    return (
        owner_urn["id"] == user.username
        and owner_urn["provider"] == settings.ARTIFACT_OWNER_PROVIDER
    )


def _trovi_artifacts(request):
    artifacts = [
        _compute_artifact_fields(a)
        for a in trovi.list_artifacts(
            request.session.get("trovi_token"), sort_by="updated_at"
        )
    ]
    return artifacts


@with_trovi_token
def index_all(request, collection=None):
    return _render_list(request, _trovi_artifacts(request))


@with_trovi_token
@login_required
def index_mine(request):
    artifacts = [
        artifact
        for artifact in _trovi_artifacts(request)
        if _owns_artifact(request.user, artifact)
    ]
    return _render_list(request, artifacts)


@with_trovi_token
def index_public(request):
    artifacts = [
        artifact
        for artifact in _trovi_artifacts(request)
        if artifact["visibility"] == "public"
    ]
    return _render_list(request, artifacts)


def _delete_artifact_version(request, version):
    if not version.doi:
        try:
            version.delete()
        except Exception:
            LOG.exception(f"Failed to delete artifact version {version}")
            messages.add_message(
                request,
                messages.ERROR,
                f"Internal error deleting artifact version {version}",
            )
            return False
        messages.add_message(
            request,
            messages.SUCCESS,
            f"Successfully deleted artifact version {version}.",
        )
        return True
    else:
        messages.add_message(
            request,
            messages.ERROR,
            f"Cannot delete versions " f"already assigned a DOI. ({version})",
        )
        return False


@check_edit_permission
@with_trovi_token
@login_required
def edit_artifact(request, artifact):
    if request.method == "POST":
        authors_formset = AuthorFormset(request.POST, initial=artifact["authors"])

        form = ArtifactForm(request.POST, artifact=artifact, request=request)

        if "delete_version" in request.POST:
            version_slug = request.POST.get("delete_version")
            try:
                trovi.delete_version(
                    request.session.get("trovi_token"), artifact["uuid"], version_slug
                )
            except trovi.TroviException:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Could not delete artifact version {}".format(version_slug),
                )
            # Return to edit form
            return HttpResponseRedirect(
                reverse("sharing_portal:edit", args=[artifact["uuid"]])
            )

        elif "delete_all" in request.POST:
            deleted_all_successfully = True
            for version in artifact["versions"]:
                try:
                    trovi.delete_version(
                        request.session.get("trovi_token"),
                        artifact["uuid"],
                        version["slug"],
                    )
                except trovi.TroviException:
                    deleted_all_successfully = False
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "Could not delete artifact version {}".format(version["slug"]),
                    )
            if not deleted_all_successfully:
                return HttpResponseRedirect(
                    reverse("sharing_portal:edit", args=[artifact["uuid"]])
                )

            messages.add_message(
                request,
                messages.SUCCESS,
                f"Successfully deleted all versions for artifact {artifact['title']}.",
            )

            # Return to Trovi home page
            return HttpResponseRedirect(reverse("sharing_portal:index_all"))

        artifact, errors = _handle_artifact_forms(
            request, form, artifact=artifact, authors_formset=authors_formset
        )
        if errors:
            (messages.add_message(request, messages.ERROR, e) for e in errors)
        else:
            messages.add_message(
                request, messages.SUCCESS, "Successfully saved artifact."
            )
        return HttpResponseRedirect(
            reverse("sharing_portal:detail", args=[artifact["uuid"]])
        )

    authors_formset = AuthorFormset(initial=artifact["authors"])
    form = ArtifactForm(artifact=artifact, request=request)
    template = loader.get_template("sharing_portal/edit.html")
    context = {
        "artifact_form": form,
        "artifact": artifact,
        "authors_formset": authors_formset,
    }

    return HttpResponse(template.render(context, request))


@check_edit_permission
@with_trovi_token
@login_required
def share_artifact(request, artifact):
    if request.method == "POST":

        form = ShareArtifactForm(request, request.POST)
        z_form = ZenodoPublishFormset(
            request.POST, artifact_versions=artifact["versions"]
        )

        if form.is_valid():
            visibility = "public" if form.cleaned_data["is_public"] else "private"
            is_reproducible = form.cleaned_data["is_reproducible"]
            reproduce_hours = form.cleaned_data["reproduce_hours"]
            patches = []
            if visibility != artifact["visibility"]:
                patches.append(
                    {"op": "replace", "path": "/visibility", "value": visibility}
                )
            if is_reproducible != artifact["reproducibility"]["enable_requests"]:
                patches.append(
                    {
                        "op": "replace",
                        "path": "/reproducibility/enable_requests",
                        "value": is_reproducible,
                    }
                )
            if reproduce_hours != artifact["reproducibility"]["access_hours"]:
                patches.append(
                    {
                        "op": "replace",
                        "path": "/reproducibility/access_hours",
                        "value": reproduce_hours,
                    }
                )
            if form.cleaned_data["project"]:
                try:
                    artifact["project"] = Project.objects.get(
                        charge_code=form.cleaned_data["project"]
                    )
                except Project.DoesNotExist:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "Project {} does not exist".format(
                            form.cleaned_data["project"]
                        ),
                    )
                    return HttpResponseRedirect(
                        reverse("sharing_portal:share", args=[artifact["uuid"]])
                    )

                    portal_project = Project.objects.get(
                        charge_code=form.cleaned_data["project"]
                    )
                    # If the user is a member of this project
                    if any(
                        [
                            user
                            for user in get_project_members(portal_project)
                            if user.username == request.user.username
                        ]
                    ):
                        trovi.set_linked_project(
                            artifact,
                            form.cleaned_data["project"],
                        )

                    if is_reproducible:
                        create_supplemental_project_if_needed(
                            request, artifact, portal_project
                        )

            if patches:
                try:
                    trovi.patch_artifact(
                        request.session.get("trovi_token"), artifact["uuid"], patches
                    )
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        "Successfully updated sharing settings.",
                    )
                except trovi.TroviException:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        "Error updating artifact in Trovi, please try again",
                    )

            if z_form.is_valid() and _request_artifact_dois(
                request, artifact, request_forms=z_form.cleaned_data
            ):
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    (
                        "Requested DOI(s) for artifact versions. The process "
                        "of issuing DOIs may take a few minutes."
                    ),
                )

            return HttpResponseRedirect(
                reverse("sharing_portal:detail", args=[artifact["uuid"]])
            )
    else:
        # Use the first linked chameleon project
        project = trovi.get_linked_project(artifact)

        form = ShareArtifactForm(
            request,
            initial={
                "is_public": artifact["visibility"] == "public",
                "is_reproducible": artifact["reproducibility"]["enable_requests"],
                "project": project,
                "reproduce_hours": artifact["reproducibility"]["access_hours"],
            },
        )
        z_form = ZenodoPublishFormset(artifact_versions=artifact["versions"])

    share_url = request.build_absolute_uri(
        reverse("sharing_portal:detail", kwargs={"pk": artifact["uuid"]})
    )
    if artifact.get("sharing_key"):
        share_url += "?{key_name}={key_value}".format(
            key_name=SHARING_KEY_PARAM, key_value=artifact["sharing_key"]
        )

    template = loader.get_template("sharing_portal/share.html")
    context = {
        "share_form": form,
        "z_management_form": z_form.management_form,
        "z_forms": _artifact_display_versions(z_form.forms),
        "share_url": share_url,
        "artifact": artifact,
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


def _parse_doi(artifact):
    if artifact["versions"]:
        contents = trovi.parse_contents_urn(artifact["versions"][-1]["contents"]["urn"])
        if contents["provider"] == "zenodo":
            return {
                "doi": contents["id"],
                "url": ZenodoClient.to_record_url(contents["id"]),
                "created_at": artifact["versions"][-1]["created_at"],
            }
    return None


@with_trovi_token
@get_artifact
def artifact(request, artifact, version_slug=None):
    # Show the launch button if the user is logged out, or has active
    # allocations. If the user is logged out, they will be asked to log in
    # after clicking launch.
    show_launch = not request.user.is_authenticated or has_active_allocations(request)

    version = _artifact_version(artifact, version_slug)
    if not version:
        if not version_slug:
            error_message = "This artifact has no versions"
        else:
            error_message = "This artifact has no version {}".format(version_slug)
        messages.add_message(request, messages.ERROR, error_message)

    if version_slug:
        launch_url = reverse(
            "sharing_portal:launch_version", args=[artifact["uuid"], version_slug]
        )
    else:
        launch_url = reverse("sharing_portal:launch", args=[artifact["uuid"]])

    # Ensure launch URLs are authenticated if a private link is being used.
    request_daypass_url = preserve_sharing_key(
        reverse("sharing_portal:request_daypass", args=[artifact["uuid"]]), request
    )
    launch_url = preserve_sharing_key(launch_url, request)

    # We use this download URL instead of the one from trovi so we can
    # automatically add headers and ensure that the link hasn't expired by
    # the time the user clicks it.
    if version_slug:
        download_url = reverse(
            "sharing_portal:download_version", args=[artifact["uuid"], version_slug]
        )
    else:
        download_url = reverse("sharing_portal:download", args=[artifact["uuid"]])
    download_url = preserve_sharing_key(download_url, request)

    access_methods = []
    if version:
        sharing_key = request.GET.get(SHARING_KEY_PARAM, None)
        try:
            access_methods = trovi.get_contents_url_info(
                request.session.get("trovi_token"),
                version["contents"]["urn"],
                sharing_key=sharing_key,
            )["access_methods"]
        except trovi.TroviException:
            LOG.error(f"Could not get contents for {version['contents']['urn']}")

    git_content = [method for method in access_methods if method["protocol"] == "git"]
    http_content = [method for method in access_methods if method["protocol"] == "http"]

    template = loader.get_template("sharing_portal/detail.html")

    context = {
        "artifact": artifact,
        "doi_info": _parse_doi(artifact),
        "version": version,
        "launch_url": launch_url,
        "download_url": download_url,
        "request_daypass_url": request_daypass_url,
        "editable": can_edit(request, artifact),
        "show_launch": show_launch,
        "git_content": git_content,
        "http_content": http_content,
    }
    template = loader.get_template("sharing_portal/detail.html")
    return HttpResponse(template.render(context, request))


@get_artifact
@with_trovi_token
@login_required
def launch(request, artifact, version_slug=None):
    version = _artifact_version(artifact, version_slug)

    if not version:
        raise Http404(
            (
                "There is no version {} for this artifact, or you do not have access.".format(
                    version_slug or ""
                )
            )
        )

    trovi_token = request.session.get("trovi_token")

    # If no allocation, redirerect to request daypass
    if artifact["reproducibility"]["enable_requests"] and not has_active_allocations(
        request
    ):
        daypass_request_url = preserve_sharing_key(
            reverse("sharing_portal:request_daypass", args=[artifact["uuid"]]), request
        )
        return redirect(daypass_request_url)
    trovi.increment_metric_count(artifact["uuid"], version["slug"], token=trovi_token)
    return redirect(
        launch_url(
            version, request, token=trovi_token, can_edit=can_edit(request, artifact)
        )
    )


def launch_url(version, request, token=None, can_edit=False):
    base_url = "{}/hub/import".format(settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
    contents_urn = version["contents"]["urn"]
    sharing_key = request.GET.get(SHARING_KEY_PARAM, None)
    contents_url_info = trovi.get_contents_url_info(
        token, contents_urn, sharing_key=sharing_key
    )["access_methods"]
    http_urls = [access for access in contents_url_info if access["protocol"] == "http"]
    git_urls = [access for access in contents_url_info if access["protocol"] == "git"]
    if http_urls:
        contents_url = http_urls[0]["url"]
        proto = "http"
    elif git_urls:
        contents_url = f"{git_urls[0]['remote']}@{git_urls[0]['ref']}"
        proto = "git"
    else:
        contents_url = ""
        proto = ""
    query = dict(
        contents_urn=contents_urn,
        contents_url=contents_url,
        contents_proto=proto,
        ownership=("own" if can_edit else "fork"),
    )
    return str(base_url + "?" + urlencode(query))


@get_artifact
@with_trovi_token
@login_required
def request_daypass(request, artifact, **kwargs):
    if not artifact or not artifact["reproducibility"]["enable_requests"]:
        raise Http404("That artifact either doesn't exist, or can't be reproduced")

    if request.method == "POST":
        form = RequestDaypassForm(
            request.POST,
            request,
        )
        if form.is_valid():
            daypass_request = DaypassRequest.objects.create(
                artifact_uuid=artifact["uuid"],
                name=form.cleaned_data["name"],
                institution=form.cleaned_data["institution"],
                reason=form.cleaned_data["reason"],
                created_by=request.user,
                status=DaypassRequest.STATUS_PENDING,
            )
            send_request_mail(daypass_request, request, artifact)

            messages.add_message(request, messages.SUCCESS, "Request submitted")
            return HttpResponseRedirect(
                preserve_sharing_key(
                    reverse("sharing_portal:detail", args=[artifact["uuid"]]), request
                )
            )
        else:
            if form.errors:
                (messages.add_message(request, messages.ERROR, e) for e in form.errors)
            return HttpResponseRedirect(
                preserve_sharing_key(
                    reverse("sharing_portal:request_daypass", args=[artifact["uuid"]]),
                    request,
                )
            )

    form = RequestDaypassForm(
        initial={
            "name": f"{request.user.first_name} {request.user.last_name}",
            "email": request.user.email,
        }
    )

    template = loader.get_template("sharing_portal/request_daypass.html")
    context = {
        "artifact": artifact,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


def send_request_mail(daypass_request, request, artifact):
    LOG.info("sending request mail")
    url = request.build_absolute_uri(
        reverse("sharing_portal:review_daypass", args=[daypass_request.id])
    )
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    list_url = request.build_absolute_uri(
        reverse("sharing_portal:list_daypass_requests")
    )
    artifact_title = artifact["title"]
    subject = f'Daypass request for "{artifact_title}"'
    body = f"""
    <p>
    A request has been made to reproduce the artifact:
    '{artifact_title}'.
    </p>
    <p>
    Review this decision by visiting <a href="{url}">this link</a>. You can
    view all pending and reviewed requests <a href="{list_url}">here</a>.
    </p>
    <p><i>This is an automatic email, please <b>DO NOT</b> reply!
    If you have any question or issue, please submit a ticket on our
    <a href="{help_url}">help desk</a>.
    </i></p>
    <p>Thanks,</p>
    <p>Chameleon Team</p>
    """
    project = Project.objects.get(charge_code=trovi.get_linked_project(artifact))
    managers = [u.email for u in get_project_membership_managers(project)]
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=managers,
        message=strip_tags(body),
        html_message=body,
    )
    LOG.info("sent mail")


@with_trovi_token
@login_required
def review_daypass(request, request_id, **kwargs):
    try:
        daypass_request = DaypassRequest.objects.get(pk=request_id)
    except DaypassRequest.DoesNotExist:
        raise Http404("That daypass request does not exist")

    daypass_request.artifact = trovi.get_artifact_by_trovi_uuid(
        request.session.get("trovi_token"), daypass_request.artifact_uuid
    )

    artifact = trovi.get_artifact_by_trovi_uuid(
        request.session.get("trovi_token"), daypass_request.artifact_uuid
    )
    project = trovi.get_linked_project(artifact)
    if not project or not is_membership_manager(project, request.user.username):
        raise PermissionDenied("You do not have permission to view that page")

    if daypass_request.status != DaypassRequest.STATUS_PENDING:
        messages.add_message(
            request,
            messages.SUCCESS,
            f"This request was already reviewed by: {daypass_request.decision_by.username}",
        )
        return HttpResponseRedirect(reverse("sharing_portal:list_daypass_requests"))

    if request.method == "POST":
        form = ReviewDaypassForm(
            request.POST,
            request,
        )
        if form.is_valid():
            status = form.cleaned_data["status"]
            daypass_request.status = status
            daypass_request.decision_at = timezone.now()
            daypass_request.decision_by = request.user
            daypass_request.save()
            send_request_decision_mail(daypass_request, request)
            messages.add_message(request, messages.SUCCESS, f"Request status: {status}")
            return HttpResponseRedirect(
                reverse("sharing_portal:detail", args=[daypass_request.artifact_uuid])
            )
        else:
            if form.errors:
                (messages.add_message(request, messages.ERROR, e) for e in form.errors)
            return HttpResponseRedirect(
                reverse("sharing_portal:review_daypass", args=[request_id])
            )

    form = ReviewDaypassForm()

    template = loader.get_template("sharing_portal/review_daypass.html")
    context = {
        "daypass_request": daypass_request,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


@login_required
def list_daypass_requests(request, **kwargs):
    keycloak_client = KeycloakClient()
    projects = [
        project["groupName"]
        for project in keycloak_client.get_user_roles(request.user.username)
        if manage_membership_in_scope(project["scopes"])
    ]
    trovi_artifacts = trovi.list_artifacts(request.session.get("trovi_token"))
    trovi_artifacts_map = {}
    # Create a map of all artifacts assigned to projects this user has perms on
    for artifact in trovi_artifacts:
        linked_project = trovi.get_linked_project(artifact)
        if linked_project and linked_project.charge_code in projects:
            trovi_artifacts_map[artifact["uuid"]] = artifact

    pending_requests = (
        DaypassRequest.objects.all()
        .filter(
            artifact_uuid__in=trovi_artifacts_map.keys(),
            status=DaypassRequest.STATUS_PENDING,
        )
        .order_by("-created_at")
    )
    for daypass_request in pending_requests:
        daypass_request.url = reverse(
            "sharing_portal:review_daypass", args=[daypass_request.id]
        )
        daypass_request.artifact = trovi_artifacts_map[daypass_request.artifact_uuid]
    reviewed_requests = (
        DaypassRequest.objects.all()
        .exclude(status=DaypassRequest.STATUS_PENDING)
        .filter(artifact_uuid__in=trovi_artifacts_map.keys())
        .order_by("-created_at")
    )
    for daypass_request in reviewed_requests:
        daypass_request.artifact = trovi_artifacts_map[daypass_request.artifact_uuid]
    template = loader.get_template("sharing_portal/list_daypass_requests.html")
    context = {
        "pending_requests": pending_requests,
        "reviewed_requests": reviewed_requests,
    }
    return HttpResponse(template.render(context, request))


def send_request_decision_mail(daypass_request, request):
    subject = f"Daypass request has been reviewed: {daypass_request.status}"
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    artifact = trovi.get_artifact_by_trovi_uuid(
        request.session.get("trovi_token"), daypass_request.artifact_uuid
    )
    artifact_title = artifact["title"]
    daypass_project = DaypassProject.objects.get(artifact_uuid=artifact["uuid"])
    reproducibility_project = daypass_project.project
    if daypass_request.status == DaypassRequest.STATUS_APPROVED:
        invite = add_project_invitation(
            reproducibility_project.id,
            daypass_request.created_by.email,
            daypass_request.decision_by,
            request.get_host(),
            artifact["reproducibility"]["access_hours"],
            False,
        )
        daypass_request.invitation = invite
        daypass_request.save()
        url = get_invite_url(request, invite.email_code)
        artifact_url = request.build_absolute_uri(
            reverse("sharing_portal:detail", args=[artifact["uuid"]])
        )
        body = f"""
        <p>
        Your daypass request to reproduce '{artifact_title}'
        has been approved. Your access is for {invite.duration} hours,
        and begins when you click <a href="{url}">this link</a>.
        </p>
        <p>
        After accepting the invitation, first you will be taken to the project
        overview page for the project you are being added to. Note that its ID,
        {reproducibility_project.charge_code}, may be required when running
        some artifacts.
        </p>
        <p>
        The artifact you requested to reproduce is located
        <a href="{artifact_url}">here</a>. You will be able to click "Launch"
        once the invitation is accepted.
        </p>
        <p>
        You can browse our documentation for using Jupyter
        <a href="https://chameleoncloud.readthedocs.io/en/latest/technical/jupyter.html">
        at this link</a>, or our Chameleon getting started guide
        <a href="https://chameleoncloud.readthedocs.io/en/latest/getting-started/index.html">
        here</a>.
        </p>
        <p><i>This is an automatic email, please <b>DO NOT</b> reply!
        If you have any question or issue, please submit a ticket on our
        <a href="{help_url}">help desk</a>.
        </i></p>
        <p>Thanks,</p>
        <p>Chameleon Team</p>
        """
    elif daypass_request.status == DaypassRequest.STATUS_REJECTED:
        body = f"""
        <p>
        Your daypass request to reproduce '{artifact_title}' has been rejected.
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
        recipient_list=[daypass_request.created_by.email],
        message=strip_tags(body),
        html_message=body,
    )


def _artifact_version(artifact, version_slug=None):
    if artifact["versions"]:
        return next(
            version
            for version in artifact["versions"]
            if not version_slug or version["slug"] == version_slug
        )
    return None


def _handle_artifact_forms(request, artifact_form, authors_formset=None, artifact=None):
    errors = []

    if artifact_form.is_valid():
        authors = None

        patches = []
        keys = ["title", "short_description", "long_description", "title", "tags"]
        for key in keys:
            value = artifact_form.cleaned_data[key]
            if artifact.get(key) != value:
                patches.append({"op": "replace", "path": f"/{key}", "value": value})

        if authors_formset:
            if authors_formset.is_valid():
                authors = []
                for author in authors_formset.cleaned_data:
                    if author and not author["DELETE"]:
                        del author["DELETE"]
                        authors.append(author)
                if authors and authors != artifact["authors"]:
                    patches.append(
                        {"op": "replace", "path": "/authors", "value": authors}
                    )
            else:
                errors.extend(authors_formset.errors)

        if not errors:
            if patches:
                try:
                    trovi.patch_artifact(
                        request.session.get("trovi_token"), artifact["uuid"], patches
                    )
                except trovi.TroviException as e:
                    errors.append(str(e))
    else:
        errors.extend(artifact_form.errors)

    return artifact, errors


def _request_artifact_dois(request, artifact, request_forms=[]):
    """Process Zenodo artifact DOI request forms.
    Returns:
        bool: if any DOIs were requested.
    """
    try:
        to_request = [
            f["artifact_version_id"] for f in request_forms if f["request_doi"]
        ]
        if to_request:
            for artifact_version_id in to_request:
                trovi.migrate_to_zenodo(
                    request.session.get("trovi_token"),
                    artifact["uuid"],
                    artifact_version_id,
                )
            return True
        return False
    except Exception:
        LOG.exception("Failed to request DOI for artifact {}".format(artifact["uuid"]))


def _artifact_display_versions(versions):
    """Return a list of artifact versions for display purposes.
    This is slightly different than the 'versions' property of the artifact, as
    it is reverse-sorted (newest at the top) and also enumerated so that while
    it's reversed, the numbers still indicate chronological order.
    """
    versions_list = list(versions)
    return [(v.model["slug"], v) for (i, v) in enumerate(reversed(versions_list))]


def create_supplemental_project_if_needed(request, artifact, project):
    try:
        DaypassProject.objects.get(artifact_uuid=artifact["uuid"])
    except DaypassProject.DoesNotExist:
        mapper = ProjectAllocationMapper(request)

        pi = project.pi
        artifact_url = request.build_absolute_uri(
            reverse("sharing_portal:detail", kwargs={"pk": artifact["uuid"]})
        )
        supplemental_project = {
            "nickname": "reproducing_{}".format(artifact["uuid"]),
            "title": "Reproducing '{}'".format(artifact["title"]),
            "description": "This project is for reproducing the artifact '{}' {}".format(
                artifact["title"], artifact_url
            ),
            "typeId": project.type.id,
            "fieldId": project.field.id,
            "piId": project.pi.id,
        }
        # Approval code is commented out during initial preview release.
        allocation_data = {
            "resourceId": 39,
            "requestorId": pi.id,
            "computeRequested": 1000,
            "status": "approved",
            # "dateReviewed": timezone.now(),
            # "start": timezone.now(),
            # "end": timezone.now() + timedelta(days=6*30),
            # "decisionSummary": "automatically approved for reproducibility",
            # "computeAllocated": 1000,
            # "justification": "Automatic decision",
        }
        supplemental_project["allocations"] = [allocation_data]
        supplemental_project["source"] = "Daypass"
        created_tas_project = mapper.save_project(
            supplemental_project, request.get_host()
        )
        # We can assume only 1 here since this project is new
        # allocation = Allocation.objects.get(project_id=created_tas_project["id"])
        # allocation.status = "approved"
        # allocation.save()

        created_project = Project.objects.get(id=created_tas_project["id"])
        daypass_project = DaypassProject(
            artifact_uuid=artifact["uuid"], project=created_project
        )
        daypass_project.save()


@check_edit_permission
@with_trovi_token
@login_required
def create_git_version(request, artifact):
    errors = False
    if request.method == "POST":
        remote_url = request.POST.get("gitRemote")
        git_ref = request.POST.get("gitRef")
        # Validate git ref
        for item in ls_remote(remote_url):
            if item[0] == git_ref:
                break
        else:
            messages.add_message(
                request,
                messages.ERROR,
                "Either invalid git reference specified, or invalid remote URL",
            )
            errors = True
        if not errors:
            try:
                trovi.create_version(
                    request.session.get("trovi_token"),
                    artifact["uuid"],
                    f"urn:trovi:contents:git:{remote_url}@{git_ref}",
                )
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Successfully created artifact version",
                )
                return HttpResponseRedirect(
                    reverse("sharing_portal:detail", args=[artifact["uuid"]])
                )
            except trovi.TroviException:
                messages.add_message(
                    request,
                    messages.ERROR,
                    "Could not create trovi artifact, are you using an HTTP(S) git remote?",
                )
    template = loader.get_template("sharing_portal/create_git_version.html")
    return HttpResponse(template.render({}, request))


# Login required to prevent someone potentially abusing this
@login_required
def get_remote_data(request):
    remote_url = request.GET.get("remote_url")
    return JsonResponse({"result": ls_remote(remote_url)})


def ls_remote(remote_url):
    remote_url = remote_url.strip()
    res = subprocess.run(["git", "ls-remote", remote_url], capture_output=True)
    output = res.stdout.decode("utf-8")
    error_output = res.stderr.decode("utf-8")
    if error_output:
        LOG.warning(f"Error output during ls-remote {remote_url}")
        LOG.warning(error_output)
    parts = []
    lines = output.strip().split("\n")
    for line in lines:
        if line:
            parts.append(line.split("\t"))
    return parts


@with_trovi_token
@login_required
def create_artifact(request):
    if request.method == "POST":
        authors_formset = AuthorCreateFormset(request.POST)
        form = ArtifactForm(request.POST, request=request)

        if form.is_valid():
            artifact_data = {
                "owner_urn": f"urn:trovi:user:{settings.ARTIFACT_OWNER_PROVIDER}:{request.user.username}",
            }
            keys = ["title", "short_description", "long_description", "title", "tags"]
            for key in keys:
                artifact_data[key] = form.cleaned_data[key]
            if authors_formset:
                authors = []
                if authors_formset.is_valid():
                    for author in authors_formset.cleaned_data:
                        if author:
                            authors.append(author)
                artifact_data["authors"] = authors
                trovi_artifact = trovi.create_new_artifact(
                    request.session.get("trovi_token"), artifact_data
                )
                messages.add_message(
                    request, messages.SUCCESS, "Successfully saved artifact."
                )
                return HttpResponseRedirect(
                    reverse(
                        "sharing_portal:create_git_version",
                        args=[trovi_artifact["uuid"]],
                    )
                )
            else:
                messages.add_message(
                    request, messages.ERROR, "Could not create artifact"
                )
        else:
            messages.add_message(request, messages.ERROR, "Could not create artifact")

    authors_formset = AuthorCreateFormset(initial=[])
    form = ArtifactForm(request=request)
    template = loader.get_template("sharing_portal/create.html")
    context = {
        "artifact_form": form,
        "authors_formset": authors_formset,
    }
    return HttpResponse(template.render(context, request))


@get_artifact
@with_trovi_token
def download(request, artifact, version_slug=None):
    version = _artifact_version(artifact, version_slug)
    sharing_key = request.GET.get(SHARING_KEY_PARAM, None)
    access_methods = trovi.get_contents_url_info(
        request.session.get("trovi_token"),
        version["contents"]["urn"],
        sharing_key=sharing_key,
    )
    for method in access_methods["access_methods"]:
        if method["protocol"] == "http" and method["method"] == "GET":
            return HttpResponseRedirect(method["url"], headers=method["headers"])
    messages.add_message(request, messages.ERROR, "Could not download this artifact")
    return HttpResponseRedirect(
        reverse("sharing_portal:detail", args=[artifact["uuid"]])
    )
