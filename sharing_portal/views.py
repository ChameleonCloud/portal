import json
import logging
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
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
    ArtifactForm,
    AuthorFormset,
    AuthorCreateFormset,
    ShareArtifactForm,
    ZenodoPublishFormset,
    RequestDaypassForm,
    ReviewDaypassForm,
    RoleFormset,
)
from .models import (
    Artifact,
    ArtifactBadge,
    Badge,
    DaypassRequest,
    DaypassProject,
    FeaturedArtifact,
)
from .zenodo import ZenodoClient

LOG = logging.getLogger(__name__)

SHARING_KEY_PARAM = "s"


class GitUrlParser:
    """
    Parse & rewrite git urls (supports GitHub and Gitlab)
    inspired from - https://github.com/nephila/giturlparse
    """

    PATTERNS = {
        "https": (
            r"((?P<protocol>https))://(?P<domain>[^:/]+)"
            r"(?P<pathname>/(?P<owner>[^/]+?)/"
            r"(?P<repo>[^/]+?)(?:(\.git)?(/)?)"
            r"(?P<path_raw>([\-\/]*blob/|[\-\/]*tree/).+)?)$"
        ),
        "ssh": (
            r"((?P<protocol>ssh))?(://)?(?P<_user>.+?)@(?P<domain>[^:/]+)(:)"
            r"(?P<pathname>/?(?P<owner>[^/]+)/"
            r"(?P<repo>[^/]+?)(?:(\.git)?(/)?)"
            r"(?P<path_raw>([\-\/]*blob/|[\-\/]*tree/).+)?)$"
        ),
        "git": (
            r"((?P<protocol>git))://(?P<domain>[^:/]+)"
            r"(?P<pathname>/(?P<owner>[^/]+?)/"
            r"(?P<repo>[^/]+?)(?:(\.git)?(/)?)"
            r"(?P<path_raw>([\-\/]*blob/|[\-\/]*tree/).+)?)$"
        ),
    }

    def __init__(self):
        self.COMPILED_PATTERNS = {
            proto: re.compile(regex, re.IGNORECASE)
            for proto, regex in self.PATTERNS.items()
        }

    def parse(self, url):
        parsed_info = defaultdict(lambda: "")
        platform = self
        for protocol, regex in platform.COMPILED_PATTERNS.items():
            match = regex.match(url)
            if not match:
                continue
            matches = match.groupdict(default="")
            # Update info with matches
            parsed_info.update(matches)
            parsed_info.update(
                {
                    "url": url,
                    "protocol": protocol,
                }
            )
        return parsed_info


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


def _compute_artifact_fields(artifact):
    artifact["badges"] = ArtifactBadge.objects.filter(
        artifact_uuid=artifact["uuid"], status=ArtifactBadge.STATUS_APPROVED
    )
    terms = artifact["title"].lower().split()
    terms.extend([f"tag:{label.lower()}" for label in artifact["tags"]])
    for name in [author["full_name"] for author in artifact["authors"]]:
        terms.extend(name.lower().split(" "))
    terms.extend([f"badge:{badge.badge.name}" for badge in artifact["badges"]])
    artifact["search_terms"] = terms
    artifact["is_private"] = artifact["visibility"] == "private"
    artifact["has_doi"] = any([_parse_doi(version) for version in artifact["versions"]])
    return artifact


def _owns_artifact(user, artifact):
    owner_urn = trovi.parse_user_urn(artifact["owner_urn"])
    return (
        owner_urn["id"] == user.username
        and owner_urn["provider"] == settings.ARTIFACT_OWNER_PROVIDER
    )


@handle_trovi_errors
def _trovi_artifacts(request, limit=20, after=None):
    kwargs = {}
    if after:
        kwargs["after"] = after
    if limit:
        kwargs["limit"] = limit
    artifacts = [
        _compute_artifact_fields(a)
        for a in trovi.list_artifacts(
            request.session.get("trovi_token"), sort_by="updated_at", **kwargs
        )
        # NOTE: Due to a bug in trovi, we must filter out the marker artifact
        if a["uuid"] != after
    ]
    return artifacts


@with_trovi_token
def _render_list(request, owned=False, public=False):
    limit = 20
    after = request.GET.get("after")

    params = {"limit": limit}
    if after:
        params["after"] = after

    next_cursor = None

    raw_artifacts = _trovi_artifacts(request, limit=limit, after=after)
    artifacts = [
        a
        for a in raw_artifacts
        if (
            (not owned or _owns_artifact(request.user, a))
            and (not public or (a["visibility"] == "public" or a["has_doi"]))
        )
    ]

    featured_uuids = {str(f.artifact_uuid) for f in FeaturedArtifact.objects.all()}
    featured_artifacts = [a for a in artifacts if a["uuid"] in featured_uuids]
    other_artifacts = [a for a in artifacts if a["uuid"] not in featured_uuids]

    if raw_artifacts:
        next_cursor = raw_artifacts[-1]["uuid"]

    # AJAX request → return HTML snippet + cursor
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render(
            request,
            "sharing_portal/includes/artifact_cards.html",
            {"artifacts": other_artifacts},
        ).content.decode("utf-8")
        featured_html = render(
            request,
            "sharing_portal/includes/artifact_cards.html",
            {"artifacts": featured_artifacts},
        ).content.decode("utf-8")
        return JsonResponse(
            {"html": html, "featured_html": featured_html, "next_cursor": next_cursor}
        )

    # Normal page load
    template = loader.get_template("sharing_portal/index.html")

    context = {
        "hub_url": settings.ARTIFACT_SHARING_JUPYTERHUB_URL,
        "artifacts": other_artifacts,
        "next_cursor": next_cursor,
        "featured_artifacts": featured_artifacts,
        "tags": [t["tag"] for t in trovi.list_tags()],
        "badges": list(Badge.objects.all()),
    }

    return HttpResponse(template.render(context, request))


@with_trovi_token
def index_all(request, collection=None):
    return _render_list(request)


@login_required
@with_trovi_token
def index_mine(request):
    return _render_list(request, owned=True)


@with_trovi_token
def index_public(request):
    return _render_list(request, public=True)


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
            f"Cannot delete versions already assigned a DOI. ({version})",
        )
        return False


def _convert_artifact_roles_to_formset_roles(roles):
    role_formset_data = defaultdict(list)
    for role in roles:
        role_formset_data[role["user"]].append(role["role"])
    return [
        {"email": trovi.get_user_info(user), "roles": role_formset_data[user]}
        for user in role_formset_data
    ]


@login_required
@handle_trovi_errors
@with_trovi_token
@check_edit_permission
def edit_artifact(request, artifact):
    if request.method == "POST":
        authors_formset = AuthorFormset(
            request.POST, initial=artifact["authors"], prefix="author"
        )
        roles_formset = RoleFormset(
            request.POST,
            initial=_convert_artifact_roles_to_formset_roles(artifact["roles"]),
            prefix="role",
        )

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

        saved = _handle_artifact_forms(
            request,
            form,
            artifact=artifact,
            authors_formset=authors_formset,
            roles_formset=roles_formset,
        )
        if saved:
            messages.add_message(
                request, messages.SUCCESS, "Successfully saved artifact."
            )
        return HttpResponseRedirect(
            reverse("sharing_portal:detail", args=[artifact["uuid"]])
        )

    authors_formset = AuthorFormset(initial=artifact["authors"], prefix="author")
    roles_formset = RoleFormset(
        initial=_convert_artifact_roles_to_formset_roles(artifact["roles"]),
        prefix="role",
    )
    form = ArtifactForm(artifact=artifact, request=request, prefix="artifact")
    template = loader.get_template("sharing_portal/edit.html")
    context = {
        "artifact_form": form,
        "artifact": artifact,
        "authors_formset": authors_formset,
        "roles_formset": roles_formset,
    }

    return HttpResponse(template.render(context, request))


@check_edit_permission
@handle_trovi_errors
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


def _parse_doi(version):
    if version is None:
        return None
    contents = trovi.parse_contents_urn(version["contents"]["urn"])
    if contents["provider"] == "zenodo":
        return {
            "doi": contents["id"],
            "url": ZenodoClient.to_record_url(contents["id"]),
            "created_at": version["created_at"],
        }
    return None


def construct_issues_url(url):
    gp = GitUrlParser()
    parsed_info = gp.parse(url)
    if parsed_info["domain"] == "github.com":
        issue_page_url = (
            f"https://{parsed_info['domain'].lower()}/"
            f"{parsed_info['owner']}/{parsed_info['repo']}/issues"
        )
    elif parsed_info["domain"] == "gitlab.com":
        issue_page_url = (
            f"https://{parsed_info['domain'].lower()}/"
            f"{parsed_info['owner']}/{parsed_info['repo']}/-/issues"
        )
    else:
        issue_page_url = ""
    return issue_page_url


@handle_trovi_errors
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
            message = f"Could not get contents for {version['contents']['urn']}"
            LOG.error(message)
            messages.error(request, message)

    git_content = [method for method in access_methods if method["protocol"] == "git"]
    feedback_url = ""
    if len(git_content) > 0:
        feedback_url = construct_issues_url(git_content[0]["remote"])
    http_content = [method for method in access_methods if method["protocol"] == "http"]

    artifact = _compute_artifact_fields(artifact)
    context = {
        "artifact": artifact,
        "linked_project": trovi.get_linked_project(artifact),
        "doi_info": _parse_doi(version),
        "version": version,
        "launch_url": launch_url,
        "download_url": download_url,
        "request_daypass_url": request_daypass_url,
        "editable": can_edit(request, artifact),
        "show_launch": show_launch,
        "git_content": git_content,
        "http_content": http_content,
        "feedback_url": feedback_url,
    }
    template = loader.get_template("sharing_portal/detail.html")
    return HttpResponse(template.render(context, request))


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
        keycloak_client, request.user.username, project
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
        "form": form,
    }
    return HttpResponse(template.render(context, request))


@login_required
@handle_trovi_errors
@with_trovi_token
def list_daypass_requests(request, **kwargs):
    keycloak_client = KeycloakClient()
    projects = UserPermissions.get_manager_projects(
        keycloak_client, request.user.username
    )
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


def _handle_artifact_forms(
    request, artifact_form, authors_formset=None, roles_formset=None, artifact=None
):
    patches = []
    form_errors = []
    if artifact_form.is_valid():
        keys = ["title", "short_description", "long_description", "title", "tags"]
        for key in keys:
            value = artifact_form.cleaned_data[key]
            if artifact.get(key) != value:
                if value == "":
                    patches.append({"op": "remove", "path": f"/{key}"})
                else:
                    patches.append({"op": "replace", "path": f"/{key}", "value": value})

    if authors_formset:
        if not authors_formset.is_valid():
            form_errors += list(authors_formset.errors)
        else:
            authors = []
            for author in authors_formset.cleaned_data:
                if author and not author["DELETE"]:
                    del author["DELETE"]
                    authors.append(author)
            if authors and authors != artifact["authors"]:
                patches.append({"op": "replace", "path": "/authors", "value": authors})

        add_roles = []
        remove_roles = []
        if roles_formset:
            if not roles_formset.is_valid():
                form_errors += list(roles_formset.errors)
            else:
                # Map roles on the existing artifact by email -> list of roles
                artifact_roles = {
                    r["email"]: r["roles"]
                    for r in _convert_artifact_roles_to_formset_roles(artifact["roles"])
                }
                new_roles = roles_formset.cleaned_data
                for user_roles in [role for role in new_roles if role]:
                    user = user_roles["email"]
                    for role in user_roles["roles"]:
                        # If any of the newly defined roles for the user are not already
                        # on the artifact, that means the user wants to assign a new
                        # role to a user
                        if role not in artifact_roles.get(user, []):
                            add_roles.append(
                                {"user": trovi.to_user_urn(user), "role": role}
                            )
                    for role in artifact_roles.get(user, []):
                        # If any of the roles on the existing artifact are not in the
                        # newly defined roles, it means the user wants to unassign
                        # the role from the user
                        if role not in user_roles["roles"]:
                            remove_roles.append(
                                {"user": trovi.to_user_urn(user), "role": role}
                            )

        if form_errors:
            for error in form_errors:
                if error:
                    messages.error(request, error)
            return False

        if patches:
            trovi.patch_artifact(
                request.session.get("trovi_token"), artifact["uuid"], patches
            )

        for role in add_roles:
            trovi.add_role(
                request.session.get("trovi_token"),
                artifact["uuid"],
                role["user"],
                role["role"],
            )

        for role in remove_roles:
            trovi.remove_role(
                request.session.get("trovi_token"),
                artifact["uuid"],
                role["user"],
                role["role"],
            )

    return True


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


@login_required
@handle_trovi_errors
@with_trovi_token
@check_edit_permission
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


@login_required
@handle_trovi_errors
@with_trovi_token
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
