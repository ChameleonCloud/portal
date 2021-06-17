import json
import logging
import re
import sys
import uuid
from datetime import datetime

from chameleon.decorators import terms_required
from chameleon.keystone_auth import admin_ks_client, get_user, sync_projects
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_POST
from keystoneauth1 import adapter
from keystoneclient.v3 import client as ks_client
from util.project_allocation_mapper import ProjectAllocationMapper

from projects.serializer import ProjectExtrasJSONSerializer

from .forms import (
    AddBibtexPublicationForm,
    AllocationCreateForm,
    EditNicknameForm,
    EditTypeForm,
    InviteUserEmailForm,
    ProjectAddUserForm,
    ProjectCreateForm,
)
from .models import Invitation, Project, ProjectExtras

logger = logging.getLogger("projects")


def project_pi_or_admin_or_superuser(user, project):
    if user.is_superuser:
        return True

    if user.groups.filter(name="Allocation Admin").count() == 1:
        return True

    if user.username == project.pi.username:
        return True

    return False


def project_member_or_admin_or_superuser(user, project, project_user):
    if project_pi_or_admin_or_superuser(user, project):
        return True

    for pu in project_user:
        if user.username == pu.username:
            return True

    return False


@login_required
def user_projects(request):
    context = {}

    username = request.user.username
    mapper = ProjectAllocationMapper(request)
    user = mapper.get_user(username)

    context["is_pi_eligible"] = user["piEligibility"].lower() == "eligible"
    context["username"] = username
    context["projects"] = mapper.get_user_projects(username, to_pytas_model=True)

    return render(request, "projects/user_projects.html", context)


@login_required
def accept_invite(request, invite_code):
    mapper = ProjectAllocationMapper(request)
    try:
        accepted, result = mapper.accept_invite(request.user, invite_code)
        if accepted:
            messages.success(request, "Accepted invitation")
            return HttpResponseRedirect(
                    reverse("projects:view_project",args=result)
            )
        else:
            messages.error(request, result)
            return HttpResponseRedirect(reverse("projects:user_projects"))
    except Invitation.DoesNotExist:
        raise Http404("That invitation does not exist!")


@login_required
def view_project(request, project_id):
    mapper = ProjectAllocationMapper(request)
    try:
        project = mapper.get_project(project_id)
        if project.source != "Chameleon":
            raise Http404("The requested project does not exist!")
    except Exception as e:
        logger.error(e)
        raise Http404("The requested project does not exist!")

    form = ProjectAddUserForm()
    invite_form = InviteUserEmailForm()
    nickname_form = EditNicknameForm()
    type_form_args = {"request": request}
    type_form = EditTypeForm(**type_form_args)
    pubs_form = AddBibtexPublicationForm()

    if request.POST and project_pi_or_admin_or_superuser(request.user, project):
        form = ProjectAddUserForm()
        if "add_user" in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                try:
                    add_username = form.cleaned_data["user_ref"]
                    if mapper.add_user_to_project(project, add_username):
                        messages.success(
                            request, f'User "{add_username}" added to project!'
                        )
                        form = ProjectAddUserForm()
                except Exception as e:
                    logger.exception("Failed adding user")
                    messages.error(
                        request,
                        (
                            "Unable to add user. Confirm that the username is "
                            "correct and corresponds to a current Chameleon user."
                            "You can also send an invite to and email address if"
                            "the user does not yet have an account."
                        ),
                    )
            else:
                messages.error(
                    request,
                    (
                        "There were errors processing your request. "
                        "Please see below for details."
                    ),
                )
        elif "del_user" in request.POST:
            try:
                del_username = request.POST["user_ref"]
                # Ensure that it's not possible to remove the PI
                if del_username in [project.pi.username, project.pi.email]:
                    raise PermissionDenied(
                        "Removing the PI from the project is not allowed."
                    )
                if mapper.remove_user_from_project(project, del_username):
                    messages.success(
                        request, 'User "%s" removed from project' % del_username
                    )
            except PermissionDenied as exc:
                messages.error(request, exc)
            except:
                logger.exception("Failed removing user")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to remove this user. Please try again",
                )
        elif "del_invite" in request.POST:
            try:
                email_code = request.POST["email_code"]
                mapper.remove_invitation(project_id, email_code)
                messages.success(
                    request, 'Invitation for "%s" removed' % email_code
                )
            except:
                logger.exception("Failed to delete invitation")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to remove this invitation. Please try again",
                )
        elif "resend_invite" in request.POST:
            try:
                email_code = request.POST["email_code"]
                mapper.resend_invitation(project_id, email_code, request.user)
                messages.success(
                    request, 'Invitation resent'
                )
            except:
                logger.exception("Failed to resend invitation")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to resend this invitation. Please try again"
                )
        elif "nickname" in request.POST:
            nickname_form = edit_nickname(request, project_id)
        elif "typeId" in request.POST:
            type_form = edit_type(request, project_id)
        elif "user_email" in request.POST:
            invite_form = invite_user(request, project_id)

    users = mapper.get_project_members(project)

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    for a in project.allocations:
        if a.start and isinstance(a.start, str):
            a.start = datetime.strptime(a.start, "%Y-%m-%dT%H:%M:%SZ")
        if a.dateRequested:
            if isinstance(a.dateRequested, str):
                a.dateRequested = datetime.strptime(
                    a.dateRequested, "%Y-%m-%dT%H:%M:%SZ"
                )
        if a.dateReviewed:
            if isinstance(a.dateReviewed, str):
                a.dateReviewed = datetime.strptime(a.dateReviewed, "%Y-%m-%dT%H:%M:%SZ")
        if a.end:
            if isinstance(a.end, str):
                a.end = datetime.strptime(a.end, "%Y-%m-%dT%H:%M:%SZ")

    user_mashup = []
    for u in users:
        user = {
            "username": u.username,
            "role": u.role,
        }
        try:
            portal_user = User.objects.get(username=u.username)
            user["email"] = portal_user.email
            user["first_name"] = portal_user.first_name
            user["last_name"] = portal_user.last_name
        except User.DoesNotExist:
            logger.info("user: " + u.username + " not found")
        user_mashup.append(user)

    invitations = mapper.get_project_invitations(project_id)
    clean_invitations = []
    for i in invitations:
        new_item = {}
        new_item["email_address"] = i.email_address
        new_item["email_code"] = i.email_code
        new_item["status"] = i.status
        clean_invitations.append(new_item)
    logger.info(clean_invitations)

    return render(
        request,
        "projects/view_project.html",
        {
            "project": project,
            "project_nickname": project.nickname,
            "project_type": project.type,
            "users": user_mashup,
            "invitations": clean_invitations,
            "is_pi": request.user.username == project.pi.username,
            "is_admin": request.user.is_superuser,
            "form": form,
            "invite_form": invite_form,
            "nickname_form": nickname_form,
            "type_form": type_form,
            "pubs_form": pubs_form,
        },
    )


def set_ks_project_nickname(chargeCode, nickname):
    for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
        ks_admin = admin_ks_client(region=region)
        project_list = ks_admin.projects.list(domain=ks_admin.user_domain_id)
        project = [
            this
            for this in project_list
            if getattr(this, "charge_code", None) == chargeCode
        ]
        logger.info(
            "Assigning nickname {0} to project with charge code {1} at {2}".format(
                nickname, chargeCode, region
            )
        )
        if project and project[0]:
            project = project[0]
        ks_admin.projects.update(project, name=nickname)
        logger.info(
            "Successfully assigned nickname {0} to project with charge code {1} at {2}".format(
                nickname, chargeCode, region
            )
        )


@login_required
@terms_required("project-terms")
def create_allocation(request, project_id, allocation_id=-1):
    mapper = ProjectAllocationMapper(request)

    user = mapper.get_user(request.user.username)
    if user["piEligibility"].lower() != "eligible":
        messages.error(
            request,
            "Only PI Eligible users can request allocations. If you would "
            "like to request PI Eligibility, please "
            '<a href="/user/profile/edit/">submit a PI Eligibility '
            "request</a>.",
        )
        return HttpResponseRedirect(reverse("projects:user_projects"))

    project = mapper.get_project(project_id)

    allocation = None
    allocation_id = int(allocation_id)
    if allocation_id > 0:
        for a in project.allocations:
            if a.id == allocation_id:
                allocation = a

    # goofiness that we should clean up later; requires data cleansing
    abstract = project.description
    if "--- Supplemental details ---" in abstract:
        additional = abstract.split("\n\n--- Supplemental details ---\n\n")
        abstract = additional[0]
        additional = additional[1].split("\n\n--- Funding source(s) ---\n\n")
        justification = additional[0]
        if len(additional) > 1:
            funding_source = additional[1]
        else:
            funding_source = ""
    elif allocation:
        justification = allocation.justification
        if "--- Funding source(s) ---" in justification:
            parts = justification.split("\n\n--- Funding source(s) ---\n\n")
            justification = parts[0]
            funding_source = parts[1]
        else:
            funding_source = ""
    else:
        justification = ""
        funding_source = ""

    if request.POST:
        form = AllocationCreateForm(
            request.POST,
            initial={
                "description": abstract,
                "supplemental_details": justification,
                "funding_source": funding_source,
            },
        )
        if form.is_valid():
            allocation = form.cleaned_data.copy()
            allocation["computeRequested"] = 20000

            # Also update the project
            project.description = allocation.pop("description", None)

            supplemental_details = allocation.pop("supplemental_details", None)

            logger.error(supplemental_details)
            funding_source = allocation.pop("funding_source", None)

            # if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            # This is required
            if not supplemental_details:
                supplemental_details = "(none)"

            logger.error(supplemental_details)

            if funding_source:
                allocation[
                    "justification"
                ] = "%s\n\n--- Funding source(s) ---\n\n%s" % (
                    supplemental_details,
                    funding_source,
                )
            else:
                allocation["justification"] = supplemental_details

            allocation["projectId"] = project_id
            allocation["requestorId"] = mapper.get_portal_user_id(request.user.username)
            allocation["resourceId"] = "39"

            if allocation_id > 0:
                allocation["id"] = allocation_id

            try:
                logger.info(
                    "Submitting allocation request for project %s: %s"
                    % (project.id, allocation)
                )
                updated_project = mapper.save_project(project.as_dict())
                mapper.save_allocation(
                    allocation, project.chargeCode, request.get_host()
                )
                messages.success(request, "Your allocation request has been submitted!")
                return HttpResponseRedirect(
                    reverse("projects:view_project", args=[updated_project["id"]])
                )
            except:
                logger.exception("Error creating allocation")
                form.add_error(
                    "__all__", "An unexpected error occurred. Please try again"
                )
        else:
            form.add_error(
                "__all__",
                "There were errors processing your request. "
                "Please see below for details.",
            )
    else:
        form = AllocationCreateForm(
            initial={
                "description": abstract,
                "supplemental_details": justification,
                "funding_source": funding_source,
            }
        )
    context = {
        "form": form,
        "project": project,
        "alloc_id": allocation_id,
        "alloc": allocation,
    }
    return render(request, "projects/create_allocation.html", context)


@login_required
@terms_required("project-terms")
def create_project(request):
    mapper = ProjectAllocationMapper(request)
    form_args = {"request": request}

    user = mapper.get_user(request.user.username)
    if user["piEligibility"].lower() != "eligible":
        messages.error(
            request,
            "Only PI Eligible users can create new projects. "
            "If you would like to request PI Eligibility, please "
            '<a href="/user/profile/edit/">submit a PI Eligibility '
            "request</a>.",
        )
        return HttpResponseRedirect(reverse("projects:user_projects"))
    if request.POST:
        form = ProjectCreateForm(request.POST, **form_args)
        if form.is_valid():
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()
            # let's check that any provided nickname is unique
            project["nickname"] = project["nickname"].strip()
            nickname_valid = (
                project["nickname"]
                and ProjectExtras.objects.filter(nickname=project["nickname"]).count()
                < 1
                and Project.objects.filter(nickname=project["nickname"]).count() < 1
            )

            if not nickname_valid:
                form.add_error("__all__", "Project nickname unavailable")
                return render(request, "projects/create_project.html", {"form": form})

            project.pop("accept_project_terms", None)

            # pi
            pi_user_id = mapper.get_portal_user_id(request.user.username)
            project["piId"] = pi_user_id

            # allocations
            allocation = {
                "resourceId": 39,
                "requestorId": pi_user_id,
                "computeRequested": 20000,
            }

            supplemental_details = project.pop("supplemental_details", None)
            funding_source = project.pop("funding_source", None)

            # if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            if not supplemental_details:
                supplemental_details = "(none)"

            if funding_source:
                allocation[
                    "justification"
                ] = "%s\n\n--- Funding source(s) ---\n\n%s" % (
                    supplemental_details,
                    funding_source,
                )
            else:
                allocation["justification"] = supplemental_details

            project["allocations"] = [allocation]

            # source
            project["source"] = "Chameleon"
            try:
                created_project = mapper.save_project(project, request.get_host())
                logger.info("newly created project: " + json.dumps(created_project))
                messages.success(request, "Your project has been created!")
                return HttpResponseRedirect(
                    reverse("projects:view_project", args=[created_project["id"]])
                )
            except:
                logger.exception("Error creating project")
                form.add_error(
                    "__all__", "An unexpected error occurred. Please try again"
                )
        else:
            form.add_error(
                "__all__",
                "There were errors processing your request. "
                "Please see below for details.",
            )
    else:
        form = ProjectCreateForm(**form_args)

    return render(request, "projects/create_project.html", {"form": form})


@login_required
def edit_project(request):
    context = {}
    return render(request, "projects/edit_project.html", context)


@require_POST
def invite_user(request, project_id):
    mapper = ProjectAllocationMapper(request)
    project = mapper.get_project(project_id)
    if not project_pi_or_admin_or_superuser(request.user, project):
        messages.error(request, "Only the project PI can invite users.")
        return InviteUserEmailForm()

    form = InviteUserEmailForm(request.POST)
    if form.is_valid(request):
        try:
            email_address = form.cleaned_data["user_email"]
            if mapper.email_exists_on_project(project_id, email_address):
                messages.error(request, "That email is tied to a user already"
                                        "on the project!")
            else:
                mapper.add_project_invitation(project_id, email_address, request.user)
                form = InviteUserEmailForm()
                messages.success(
                    request,
                    "Invite sent!".format(request.path),
                )
        except Exception as e:
            logger.error(e)
            messages.error(request, "Problem sending invite")
    else:
        messages.error(request, "Email address is not valid")
    return form


@require_POST
def edit_nickname(request, project_id):
    mapper = ProjectAllocationMapper(request)
    project = mapper.get_project(project_id)
    if not project_pi_or_admin_or_superuser(request.user, project):
        messages.error(request, "Only the project PI can update nickname.")
        return EditNicknameForm()

    form = EditNicknameForm(request.POST)
    if form.is_valid(request):
        # try to update nickname
        try:
            nickname = form.cleaned_data["nickname"]
            ProjectAllocationMapper.update_project_nickname(project_id, nickname)
            form = EditNicknameForm()
            set_ks_project_nickname(project.chargeCode, nickname)
            messages.success(
                request,
                "Update successful! Click <a href='{}'>here</a> to reload".format(
                    request.path
                ),
            )
        except:
            messages.error(request, "Nickname not available")
    else:
        messages.error(request, "Nickname not available")

    return form


@require_POST
def edit_type(request, project_id):
    form_args = {"request": request}
    if not request.user.is_superuser:
        messages.error(request, "Only the admin users can update project type.")
        return EditTypeForm(**form_args)

    form = EditTypeForm(request.POST, **form_args)
    if form.is_valid(request):
        # try to update type
        try:
            project_type_id = int(form.cleaned_data["typeId"])
            ProjectAllocationMapper.update_project_type(project_id, project_type_id)
            form = EditTypeForm(**form_args)
            messages.success(
                request,
                "Update successful! Click <a href='{}'>here</a> to reload".format(
                    request.path
                ),
            )
        except Exception:
            logger.exception("Failed to update project type")
            messages.error(request, "Failed to update project type")
    else:
        messages.error(request, "Failed to update project type")

    return form


def get_extras(request):
    provided_token = request.GET.get("token") if request.GET.get("token") else None
    stored_token = getattr(settings, "PROJECT_EXTRAS_API_TOKEN", None)
    if not provided_token or not stored_token or provided_token != stored_token:
        logger.error("Project Extras json api Access Token validation failed")
        return HttpResponseForbidden()

    logger.info("Get all project extras json endpoint requested")
    response = {"status": "success"}
    try:
        serializer = ProjectExtrasJSONSerializer()
        response["message"] = ""
        extras = json.loads(serializer.serialize(ProjectExtras.objects.all()))
        response["result"] = extras
    except ProjectExtras.DoesNotExist:
        response["message"] = "Does not exist."
        response["result"] = None
    return JsonResponse(response)
