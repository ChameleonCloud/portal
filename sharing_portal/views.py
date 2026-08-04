import json
import logging
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from projects.models import Project, Tag
from projects.util import get_project_members
from projects.views import (
    UserPermissions,
    add_project_invitation,
    get_project_membership_managers,
)
from util.keycloak_client import KeycloakClient
from util.project_allocation_mapper import ProjectAllocationMapper
from . import trovi
from .forms import (
    ShareArtifactForm,
    ZenodoPublishFormset,
    RequestDaypassForm,
    ReviewDaypassForm,
)
from .models import (
    Artifact,
    ArtifactBadge,
    Badge,
    DaypassRequest,
    DaypassProject,
)

LOG = logging.getLogger(__name__)

SHARING_KEY_PARAM = "s"


def trovi_redirect(redirect_to):
    """
    Decorator to mark a view as deprecated.
    redirect_to: a callable taking (request, *args, **kwargs) and returning a URL
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            new_url = redirect_to(request, *args, **kwargs)
            LOG.info("REDIRECTING REQUEST TO " + new_url)

            return HttpResponseRedirect(new_url)

        return _wrapped_view

    return decorator


def with_trovi_token(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Logged out users have no session to exchange for a token
            return view_func(request, *args, **kwargs)

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
                LOG.warning(
                    (
                        "Could not refresh Trovi token because user's access token is "
                        "unexpectedly not available in the session."
                    )
                )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def handle_trovi_errors(view_func):
    def format_error(m):
        if not isinstance(m, dict):
            try:
                m = json.loads(m)
            except json.JSONDecodeError:
                return str(m)
        new_message = ""
        for key in m:
            value = m[key]
            if isinstance(value, dict):
                new_message += f"{key}: {format_error(value)} "
            else:
                new_message += f"{key}: {value}"
        return new_message

    def _wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except trovi.TroviException as e:
            LOG.exception(e)
            messages.error(request, format_error(e.detail))
            return HttpResponseRedirect(
                reverse("sharing_portal:edit", args=[kwargs.get("pk")])
            )

    return _wrapped_view


def can_edit(request, artifact):
    return any(
        role["user"] == trovi.to_user_urn(request.user.username)
        for role in artifact["roles"]
    )


def handle_get_artifact(request, uuid, sharing_key=None):
    try:
        UUID(uuid)
        return trovi.get_artifact_by_trovi_uuid(
            uuid, request.session.get("trovi_token"), sharing_key=sharing_key
        )
    except ValueError:
        raise Http404("That artifact does not exist")
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


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts"
)
def index_all(request, collection=None):
    pass


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts?owned=1"
)
def index_mine(request):
    pass


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts?public=1"
)
def index_public(request):
    pass


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts/{kwargs['pk']}/edit/"
)
def edit_artifact(request, artifact=None):
    pass


@login_required
@handle_trovi_errors
@with_trovi_token
@check_edit_permission
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
                    portal_project = Project.objects.get(
                        charge_code=form.cleaned_data.get("project")
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

            if patches:
                trovi.patch_artifact(
                    request.session.get("trovi_token"), artifact["uuid"], patches
                )
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Successfully updated sharing settings.",
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
    user_projects = mapper.get_user_projects(request.user, to_pytas_model=False)
    for project in user_projects:
        for allocation in project["allocations"]:
            if allocation["status"].lower() == "active":
                return True
    return False


def preserve_sharing_key(url, request):
    if SHARING_KEY_PARAM in request.GET:
        return url + "?{}={}".format(SHARING_KEY_PARAM, request.GET[SHARING_KEY_PARAM])
    return url


@trovi_redirect(
    lambda request, *args, **kwargs: (
        f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts/{kwargs['pk']}"
        + (f"/versions/{kwargs['version_slug']}" if kwargs.get("version_slug") else "")
        + "/"
    )
)
def artifact(request, artifact=None, version_slug=None):
    pass


@login_required
@handle_trovi_errors
@with_trovi_token
@get_artifact
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
            artifact["uuid"],
            version,
            request,
            token=trovi_token,
            can_edit=can_edit(request, artifact),
        )
    )


def launch_url(artifact_uuid, version, request, token=None, can_edit=False):
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
        uuid=artifact_uuid,
        version_slug=version["slug"],
        contents_urn=contents_urn,
        contents_url=contents_url,
        contents_proto=proto,
        ownership=("own" if can_edit else "fork"),
    )
    repo_url = request.GET.get("repo_url")
    if repo_url:
        query["repo_url"] = repo_url
    return str(base_url + "?" + urlencode(query))


@login_required
@with_trovi_token
@get_artifact
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
            send_request_mail(request, daypass_request, artifact)

            messages.add_message(request, messages.SUCCESS, "Request submitted")
            return HttpResponseRedirect(
                preserve_sharing_key(
                    reverse("sharing_portal:detail", args=[artifact["uuid"]]), request
                )
            )
        else:
            if form.errors:
                for e in form.errors:
                    messages.add_message(request, messages.ERROR, e)
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


def send_request_mail(request, daypass_request, artifact):
    LOG.info("sending request mail")
    url = request.build_absolute_uri(
        reverse(
            "sharing_portal:review_daypass", args=[artifact["uuid"], daypass_request.id]
        )
    )
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    list_url = request.build_absolute_uri(
        reverse("sharing_portal:list_daypass_requests", args=[artifact["uuid"]])
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
    project = trovi.get_linked_project(artifact)
    if not project:
        LOG.error("Daypass request was made for artifact without linked project!")
        return
    managers = [u.email for u in get_project_membership_managers(project)]
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=managers,
        message=strip_tags(body),
        html_message=body,
    )
    LOG.info("sent mail")


@login_required
@with_trovi_token
def review_daypass(request, request_id, **kwargs):
    try:
        daypass_request = DaypassRequest.objects.get(pk=request_id)
    except DaypassRequest.DoesNotExist:
        raise Http404("That daypass request does not exist")

    artifact = trovi.get_artifact_by_trovi_uuid(
        daypass_request.artifact_uuid,
        # We use the admin token for this, because the PI is approving a Chameleon
        # allocation for an artifact that they may not own. Therefore, they won't be
        # able to view it. We should not expose any details about this artifact
        # to the PI at any point because of this.
        trovi.get_client_admin_token(),
    )
    project = trovi.get_linked_project(artifact)
    if not project:
        raise Http404("Project linked to this artifact does not exist.")
    keycloak_client = KeycloakClient()
    user_permission = UserPermissions.get_user_permissions(
        keycloak_client, request.user, project
    )
    if not user_permission.manage:
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
            try:
                daypass_project = DaypassProject.objects.get(
                    artifact_uuid=artifact["uuid"]
                )
            except DaypassProject.DoesNotExist:
                messages.error(
                    request,
                    "A daypass project for this artifact does not exist. "
                    "Try disabling and re-enabling reproducibility requests "
                    "in the share menu.",
                )
                return HttpResponseRedirect(
                    reverse(
                        "sharing_portal:review_daypass",
                        args=[artifact["uuid"], request_id],
                    )
                )
            status = form.cleaned_data["status"]
            daypass_request.status = status
            daypass_request.decision_at = timezone.now()
            daypass_request.decision_by = request.user
            daypass_request.save()
            send_request_decision_mail(request, daypass_request, daypass_project)
            messages.add_message(request, messages.SUCCESS, f"Request status: {status}")
            return HttpResponseRedirect(
                reverse("sharing_portal:detail", args=[daypass_request.artifact_uuid])
            )
        else:
            if form.errors:
                for e in form.errors:
                    messages.add_message(request, messages.ERROR, e)
            return HttpResponseRedirect(
                reverse(
                    "sharing_portal:review_daypass", args=[artifact["uuid"], request_id]
                )
            )

    form = ReviewDaypassForm()

    template = loader.get_template("sharing_portal/review_daypass.html")
    context = {
        "daypass_request": daypass_request,
        "artifact": artifact,
        "form": form,
    }
    return HttpResponse(template.render(context, request))


@login_required
@handle_trovi_errors
@with_trovi_token
def list_daypass_requests(request, **kwargs):
    keycloak_client = KeycloakClient()
    projects = UserPermissions.get_manager_projects(keycloak_client, request.user)
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
            artifact_uuid__in=trovi_artifacts_map,
            status=DaypassRequest.STATUS_PENDING,
        )
        .order_by("-created_at")
    )
    for daypass_request in pending_requests:
        daypass_request.url = reverse(
            "sharing_portal:review_daypass",
            args=[daypass_request.artifact_uuid, daypass_request.id],
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


@handle_trovi_errors
@with_trovi_token
def send_request_decision_mail(request, daypass_request, daypass_project):
    subject = f"Daypass request has been reviewed: {daypass_request.status}"
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    artifact = trovi.get_artifact_by_trovi_uuid(
        daypass_request.artifact_uuid, trovi.get_client_admin_token()
    )
    artifact_title = artifact["title"]
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
        url = invite.get_invite_url(request)
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
        try:
            return next(
                version
                for version in artifact["versions"]
                if not version_slug or version["slug"] == version_slug
            )
        except StopIteration:
            raise Http404(f"Version {version_slug} not found")
    return None


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
    """Return a list of artifact versions for display purposes."""
    versions_list = list(versions)
    return [(v.model["slug"], v) for v in versions_list]


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
            "tagId": project.tag.id,
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
        daypass_tag = Tag.objects.get(name="Daypass")
        mapper.update_project_tag(created_project.id, daypass_tag.id)
        daypass_project = DaypassProject(
            artifact_uuid=artifact["uuid"], project=created_project
        )
        daypass_project.save()


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts/{kwargs['pk']}/edit/"
)
def create_git_version(request, artifact=None):
    pass


def get_remote_data(request):
    # NOTE: We may want to set this to some token auth in the future to
    # minimize abuse. `ls_remote` is basically just HTTP GET to the repo
    # URL, so I don't think it's a big risk.
    remote_url = request.GET.get("remote_url")
    response = JsonResponse({"result": ls_remote(remote_url)})
    response["Access-Control-Allow-Origin"] = "*"
    return response


def ls_remote(remote_url):
    remote_url = remote_url.strip()
    # Need to set `cwd=/tmp` to avoid git issues with dev container
    res = subprocess.run(
        ["git", "ls-remote", remote_url], capture_output=True, cwd="/tmp"
    )
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


@trovi_redirect(
    lambda request, *args, **kwargs: f"{settings.TROVI_DASHBOARD_URL_BASE}/artifacts/add"
)
def create_artifact(request):
    pass


@handle_trovi_errors
@with_trovi_token
@get_artifact
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


def badges_api(request):
    response = HttpResponse(
        json.dumps(
            {
                "badges": [
                    {
                        "name": b.name,
                        "description": b.description,
                        "redirect_link": b.redirect_link,
                    }
                    for b in Badge.objects.filter()
                ],
                "artifact_badges": [
                    {
                        "artifact_uuid": a.artifact_uuid,
                        "badge": a.badge.name,
                    }
                    for a in ArtifactBadge.objects.filter(
                        status=ArtifactBadge.STATUS_APPROVED, deleted_at=None
                    )
                ],
            }
        ),
        content_type="application/json",
    )
    # Allow any origin to access this badge for API access
    response["Access-Control-Allow-Origin"] = "*"
    return response


@login_required
@handle_trovi_errors
@with_trovi_token
@check_edit_permission
def delete_artifact(request, artifact):
    if request.method == "POST":
        trovi.delete_artifact(request.session.get("trovi_token"), artifact["uuid"])
        return JsonResponse({"redirect_url": reverse("sharing_portal:index_all")})
    return JsonResponse({"error": "Invalid method"}, status=405)
