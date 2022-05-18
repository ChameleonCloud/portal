import json
import logging
from datetime import datetime

from chameleon.decorators import terms_required
from chameleon.keystone_auth import admin_ks_client
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.core.validators import validate_email
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
from django.forms.models import model_to_dict
from django import forms
from projects.models import Funding
from util.project_allocation_mapper import ProjectAllocationMapper
from util.keycloak_client import KeycloakClient

from projects.serializer import ProjectExtrasJSONSerializer
from . import membership

from .forms import (
    AddBibtexPublicationForm,
    AllocationCreateForm,
    ConsentForm,
    EditNicknameForm,
    EditPIForm,
    EditTypeForm,
    FundingFormset,
    ProjectAddUserForm,
    ProjectAddBulkUserForm,
    ProjectCreateForm,
)
from .models import Invitation, Project, ProjectExtras
from .util import email_exists_on_project, get_project_members, get_charge_code
from allocations.models import Allocation, Charge
from balance_service.utils import su_calculators

logger = logging.getLogger("projects")

ROLES = ["Manager", "Member"]


class UserNotPIEligible(Exception):
    pass


def is_admin_or_superuser(user):
    if user.is_superuser:
        return True

    if user.groups.filter(name="Allocation Admin").count() == 1:
        return True

    return False


def project_member_or_admin_or_superuser(user, project, project_user):
    if is_admin_or_superuser(user):
        return True

    if user.username == project.pi.username:
        return True

    for pu in project_user:
        if user.username == pu.username:
            return True

    return False


def get_user_project_role_scopes(keycloak_client, username, project):
    role, scopes = keycloak_client.get_user_project_role_scopes(
        username, get_charge_code(project)
    )
    return role, scopes


def manage_membership_in_scope(scopes):
    return "manage-membership" in scopes


def manage_project_in_scope(scopes):
    return "manage" in scopes


def get_user_permissions(keycloak_client, username, project):
    role, scopes = get_user_project_role_scopes(keycloak_client, username, project)
    return manage_membership_in_scope(scopes), manage_project_in_scope(scopes)


def is_pi_eligible(user):
    return user.pi_eligibility().lower() == "eligible"


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
    invitation = None
    try:
        invitation = Invitation.objects.get(email_code=invite_code)
    except Invitation.DoesNotExist:
        raise Http404("That invitation does not exist!")

    user = request.user
    # Check for existing daypass, use this invite instead
    daypass = get_daypass(user.id, invitation.project.id)
    try:
        if accept_invite_for_user(user, invitation, mapper):
            messages.success(request, "Accepted invitation")
            return HttpResponseRedirect(
                reverse("projects:view_project", args=[invitation.project.id])
            )
        else:
            messages.error(request, invitation.get_cant_accept_reason())
            return HttpResponseRedirect(reverse("projects:user_projects"))
    finally:
        if daypass is not None:
            daypass.delete()


def accept_invite_for_user(user, invitation, mapper):
    if invitation.can_accept():
        invitation.accept(user)
        project = mapper.get_project(invitation.project.id)
        user_ref = invitation.user_accepted.username
        membership.add_user_to_project(project, user_ref)
        return True
    return False


def get_daypass(user_id, project_id, status=Invitation.STATUS_ACCEPTED):
    try:
        return Invitation.objects.get(
            status=status,
            user_accepted_id=user_id,
            project_id=project_id,
            duration__isnull=False,
        )
    except Invitation.DoesNotExist:
        return None


def get_invitations_beyond_duration():
    duration_limited_invites = Invitation.objects.filter(
        status=Invitation.STATUS_ACCEPTED, duration__isnull=False
    )
    return [
        i
        for i in duration_limited_invites
        if i.date_exceeds_duration() < timezone.now()
    ]


def format_timedelta(timedelta_instance):
    # Formats a timedelta object so it can be displayed with a daypass user.
    # This implementation removes the fractional seconds portion of the string.
    return str(timedelta_instance).split(".")[0]


def get_invite_url(request, code):
    return request.build_absolute_uri(
        reverse("projects:accept_invite", kwargs={"invite_code": code})
    )


@login_required
def view_project(request, project_id):
    mapper = ProjectAllocationMapper(request)
    keycloak_client = KeycloakClient()

    try:
        project = mapper.get_project(project_id)
    except Exception as e:
        logger.error(e)
        raise Http404("The requested project does not exist!")

    form = ProjectAddUserForm()
    nickname_form = EditNicknameForm()
    type_form_args = {"request": request}
    type_form = EditTypeForm(**type_form_args)
    pubs_form = AddBibtexPublicationForm()
    pi_form = EditPIForm()
    bulk_user_form = ProjectAddBulkUserForm()

    can_manage_project_membership, can_manage_project = get_user_permissions(
        keycloak_client, request.user.username, project
    )

    if (
        request.POST
        and can_manage_project_membership
        or is_admin_or_superuser(request.user)
    ):
        form = ProjectAddUserForm()
        if "add_user" in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                if _add_users_to_project(
                    request,
                    project,
                    project_id,
                    [form.cleaned_data["user_ref"].strip()],
                ):
                    form = ProjectAddUserForm()
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
                if membership.remove_user_from_project(project, del_username):
                    messages.success(
                        request, 'User "%s" removed from project' % del_username
                    )
                user = User.objects.get(username=del_username)
                daypass = get_daypass(user.id, project_id)
                if daypass:
                    daypass.delete()
            except PermissionDenied as exc:
                messages.error(request, exc)
            except Exception:
                logger.exception("Failed removing user")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to remove this user. Please try again",
                )
        elif "change_role" in request.POST:
            try:
                role_username = request.POST["user_ref"]
                role_name = request.POST["user_role"].lower()
                keycloak_client.set_user_project_role(
                    role_username, get_charge_code(project), role_name
                )
            except Exception:
                logger.exception("Failed to change user role")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to change role for this user. Please try again",
                )
        elif "del_invite" in request.POST:
            try:
                invite_id = request.POST["invite_id"]
                remove_invitation(invite_id)
                messages.success(request, "Invitation removed")
            except Exception:
                logger.exception("Failed to delete invitation")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to remove this invitation. Please try again",
                )
        elif "resend_invite" in request.POST:
            try:
                invite_id = request.POST["invite_id"]
                resend_invitation(invite_id, request.user, request)
                messages.success(request, "Invitation resent")
            except Exception:
                logger.exception("Failed to resend invitation")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to resend this invitation. Please try again",
                )
        elif "nickname" in request.POST:
            nickname_form = edit_nickname(request, project_id)
        elif "typeId" in request.POST:
            type_form = edit_type(request, project_id)
        elif "pi_username" in request.POST:
            pi_form = edit_pi(request, project_id)
        elif "add_bulk_users" in request.POST:
            bulk_user_form = ProjectAddBulkUserForm(request.POST)
            if bulk_user_form.is_valid():
                usernames = [
                    username.strip()
                    for username in bulk_user_form.cleaned_data[
                        "username_csv"
                    ].splitlines()
                    if username.strip()
                ]
                if _add_users_to_project(request, project, project_id, usernames):
                    bulk_user_form = ProjectAddBulkUserForm()

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

    users = get_project_members(project)
    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    user_roles = keycloak_client.get_roles_for_all_project_members(
        get_charge_code(project)
    )
    users_mashup = []

    for u in users:
        if u.username == project.pi.username:
            continue
        u_role = user_roles.get(u.username, "member")
        user = {
            "id": u.id,
            "username": u.username,
            "role": u_role.title(),
        }
        try:
            portal_user = User.objects.get(username=u.username)
            user["email"] = portal_user.email
            user["first_name"] = portal_user.first_name
            user["last_name"] = portal_user.last_name
            # Add if the user is on a daypass
            existing_daypass = get_daypass(portal_user.id, project_id)
            if existing_daypass:
                user["daypass"] = format_timedelta(
                    existing_daypass.date_exceeds_duration() - timezone.now()
                )
        except User.DoesNotExist:
            logger.info("user: " + u.username + " not found")
        users_mashup.append(user)

    invitations = Invitation.objects.filter(project=project_id)
    invitations = [i for i in invitations if i.can_accept()]

    clean_invitations = []
    for i in invitations:
        new_item = {}
        new_item["email_address"] = i.email_address
        new_item["id"] = i.id
        new_item["status"] = i.status.title()
        if i.duration:
            new_item["duration"] = i.duration
        clean_invitations.append(new_item)

    is_on_daypass = get_daypass(request.user.id, project_id) is not None

    return render(
        request,
        "projects/view_project.html",
        {
            "project": project,
            "project_nickname": project.nickname,
            "project_type": project.type,
            "users": users_mashup,
            "invitations": clean_invitations,
            "can_manage_project_membership": can_manage_project_membership,
            "can_manage_project": can_manage_project,
            "is_admin": request.user.is_superuser,
            "is_on_daypass": is_on_daypass,
            "form": form,
            "nickname_form": nickname_form,
            "type_form": type_form,
            "pi_form": pi_form,
            "pubs_form": pubs_form,
            "bulk_user_form": bulk_user_form,
            "roles": ROLES,
            "host": request.get_host(),
        },
    )


def _add_users_to_project(request, project, project_id, user_refs):
    """
    Adds all users specified either by username or email. Returns True if all
    users were added with no errors.
    """
    success_messages = []
    error_messages = []
    for user_ref in user_refs:
        try:
            add_username = user_ref
            _ = User.objects.get(username=add_username)
            if membership.add_user_to_project(project, add_username):
                success_messages.append(f'User "{add_username}" added to project!')
        except User.DoesNotExist:
            # Try sending an invite
            email_address = user_ref
            try:
                validate_email(email_address)
                if email_exists_on_project(project, email_address):
                    error_messages.append(
                        f"The email '{user_ref}' is tied to a user already on "
                        "this project!",
                    )
                else:
                    add_project_invitation(
                        project.id,
                        email_address,
                        request.user,
                        request,
                        None,
                    )
                    success_messages.append(f"Invite sent to '{user_ref}'!")
            except ValidationError:
                error_messages.append(
                    (
                        f"Unable to add user '{user_ref}'. Confirm that the username "
                        "is correct and corresponds to a current "
                        "Chameleon user. You can also send an invite "
                        "to an email address if the user does not yet "
                        "have an account."
                    ),
                )
            except Exception:
                logger.exception(f"Failed sending invite to '{user_ref}'")
                error_messages.append(
                    f"Problem sending invite to {user_ref}, please try again."
                )
        except Exception:
            logger.exception(f"Failed adding user '{user_ref}'")
            error_messages.append("Unable to add user '{user_ref}'. Please try again.")

    if not error_messages:
        # If only successes, then either show the message or merge them together
        if len(user_refs) == 1:
            messages.success(request, success_messages[0])
        else:
            messages.success(request, "Successfully added/invited all users")
        return True
    else:
        # Else print out errors
        if success_messages:
            messages.info(
                request,
                f"Successfully added/invited {len(success_messages)} users, but had errors for {len(error_messages)} users. See messages below",
            )
        for message in error_messages:
            messages.error(request, message)
        return False


def remove_invitation(invite_id):
    invitation = Invitation.objects.get(pk=invite_id)
    invitation.delete()


def resend_invitation(invite_id, user_issued, request):
    invitation = Invitation.objects.get(pk=invite_id)
    # Make the old invitation expire
    invitation.date_expires = timezone.now()
    invitation.save()
    # Send a new invitation
    project_id = invitation.project.id
    add_project_invitation(
        project_id, invitation.email_address, user_issued, request, None
    )


def add_project_invitation(
    project_id, email_address, user_issued, request, duration, send_email=True
):
    project = Project.objects.get(pk=project_id)
    invitation = Invitation(
        project=project,
        email_address=email_address,
        user_issued=user_issued,
        duration=duration,
    )
    invitation.save()
    if send_email:
        send_invitation_email(invitation, request)
    return invitation


def send_invitation_email(invitation, request):
    project_title = invitation.project.title
    project_charge_code = invitation.project.charge_code
    url = get_invite_url(request, invitation.email_code)
    help_url = request.build_absolute_uri(reverse("djangoRT:mytickets"))
    subject = f'Invitation for project "{project_title}" ({project_charge_code})'
    body = f"""
    <p>
    You have been invited to join the Chameleon project "{project_title}"
    ({project_charge_code}).
    </p>
    <p>
    Join by clicking <a href="{url}">this link</a>,
    or by going to {url} in your browser. Once there, you will be asked to
    sign into an existing Chameleon account, or create one.
    </p>
    <p>
    This invitation will expire in
    {Invitation.default_days_until_expiration()} days.
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
        recipient_list=[invitation.email_address],
        message=strip_tags(body),
        html_message=body,
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


def _save_fundings(funding_formset, project_id):
    saved_fundings = []
    for funding_form in funding_formset:
        if hasattr(funding_form, "cleaned_data"):
            funding_dict = funding_form.cleaned_data.copy()
            funding = Funding(**funding_dict)
            funding.project_id = project_id
            funding.is_active = True
            funding.save()
            saved_fundings.append(funding_dict)
    return saved_fundings


def _remove_fundings(before_list, after_list):
    after_id_list = [f["id"] for f in after_list if f.get("id")]
    for f in before_list:
        if f and f["id"] not in after_id_list:
            f["project_id"] = f.pop("project")
            funding = Funding(**f)
            funding.is_active = False
            funding.save()


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

    abstract = project.description
    if allocation:
        justification = allocation.justification
    else:
        justification = ""

    funding_source = [
        model_to_dict(f)
        for f in Funding.objects.filter(project__id=project_id, is_active=True)
    ]
    # add extra form
    funding_source.append({})

    if request.POST:
        form = AllocationCreateForm(
            request.POST,
            initial={
                "description": abstract,
                "justification": justification,
            },
        )
        formset = FundingFormset(
            request.POST,
            initial=funding_source,
        )
        consent_form = ConsentForm(request.POST)
        if form.is_valid() and formset.is_valid() and consent_form.is_valid():
            allocation = form.cleaned_data.copy()
            allocation["computeRequested"] = 20000

            # Also update the project and fundings
            project.description = allocation.pop("description", None)
            justification = allocation.pop("justification", None)

            allocation["projectId"] = project_id
            allocation["requestorId"] = mapper.get_portal_user_id(request.user.username)
            allocation["resourceId"] = "39"
            allocation["justification"] = justification

            if allocation_id > 0:
                allocation["id"] = allocation_id

            try:
                logger.info(
                    "Submitting allocation request for project %s: %s"
                    % (project.id, allocation)
                )
                with transaction.atomic():
                    updated_project = mapper.save_project(project.as_dict())
                    mapper.save_allocation(
                        allocation, project.chargeCode, request.get_host()
                    )
                    new_funding_source = _save_fundings(formset, project_id)
                    _remove_fundings(funding_source, new_funding_source)
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
                "justification": justification,
            }
        )
        formset = FundingFormset(initial=funding_source)
        consent_form = ConsentForm()
    context = {
        "form": form,
        "funding_formset": formset,
        "consent_form": consent_form,
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
        allocation_form = AllocationCreateForm(
            request.POST, initial={"publication_up_to_date": True}
        )
        allocation_form.fields["publication_up_to_date"].widget = forms.HiddenInput()
        funding_formset = FundingFormset(request.POST, initial=[{}])
        consent_form = ConsentForm(request.POST)
        if (
            form.is_valid()
            and allocation_form.is_valid()
            and funding_formset.is_valid()
            and consent_form.is_valid()
        ):
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()
            allocation_data = allocation_form.cleaned_data.copy()
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

            # pi
            pi_user_id = mapper.get_portal_user_id(request.user.username)
            project["piId"] = pi_user_id

            # allocations
            allocation = {
                "resourceId": 39,
                "requestorId": pi_user_id,
                "computeRequested": 20000,
                "justification": allocation_data.pop("justification", None),
            }

            project["allocations"] = [allocation]
            project["description"] = allocation_data.pop("description", None)

            # source
            project["source"] = "Chameleon"
            created_project = None
            try:
                with transaction.atomic():
                    created_project = mapper.save_project(project, request.get_host())
                    _save_fundings(funding_formset, created_project["id"])
                logger.info("newly created project: " + json.dumps(created_project))
                messages.success(request, "Your project has been created!")
                return HttpResponseRedirect(
                    reverse("projects:view_project", args=[created_project["id"]])
                )
            except:
                # delete project from keycloak
                if created_project:
                    keycloak_client = KeycloakClient()
                    keycloak_client.delete_project(created_project["chargeCode"])
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
        allocation_form = AllocationCreateForm(initial={"publication_up_to_date": True})
        allocation_form.fields["publication_up_to_date"].widget = forms.HiddenInput()
        funding_formset = FundingFormset(initial=[{}])
        consent_form = ConsentForm()

    return render(
        request,
        "projects/create_project.html",
        {
            "form": form,
            "allocation_form": allocation_form,
            "funding_formset": funding_formset,
            "consent_form": consent_form,
        },
    )


@login_required
def edit_project(request):
    context = {}
    return render(request, "projects/edit_project.html", context)


@require_POST
def edit_nickname(request, project_id):
    mapper = ProjectAllocationMapper(request)
    project = mapper.get_project(project_id)

    keycloak_client = KeycloakClient()
    _, can_manage_project = get_user_permissions(
        keycloak_client, request.user.username, project
    )

    if not (can_manage_project or is_admin_or_superuser(request.user)):
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
                "Update successful! Please refresh the page.",
            )
        except Exception:
            logger.exception("Failed to update project type")
            messages.error(request, "Failed to update project type")
    else:
        messages.error(request, "Failed to update project type")

    return form


@require_POST
def edit_pi(request, project_id):
    if not request.user.is_superuser:
        messages.error(request, "Only the admin users can update project PI.")
        return EditPIForm(request.POST)

    form = EditPIForm(request.POST)
    if form.is_valid():
        project_pi_username = form.cleaned_data["pi_username"]
        # try to update PI
        try:
            new_pi = User.objects.get(username=project_pi_username)
            if not is_pi_eligible(new_pi):
                raise UserNotPIEligible()
            ProjectAllocationMapper.update_project_pi(project_id, project_pi_username)
            form = EditPIForm(request.POST)
            messages.success(
                request,
                "Update successful! Please refresh the page.",
            )
        except User.DoesNotExist:
            messages.error(
                request,
                f"Failed to update project PI. The user {project_pi_username} does not exist.",
            )
        except User.MultipleObjectsReturned:
            messages.error(
                request,
                f"Failed to update project PI. Multiple {project_pi_username} were found.",
            )
        except UserNotPIEligible:
            messages.error(
                request,
                f"Failed to update project PI. The user {project_pi_username} is not PI Eligible.",
            )
        except Exception:
            logger.exception("Failed to update project PI.")
            messages.error(request, "Failed to update project PI.")
    else:
        messages.error(request, "Failed to update project PI.")

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


def get_project_membership_managers(project):
    users = get_project_members(project)
    return [user for user in users if is_membership_manager(project, user.username)]


def is_membership_manager(project, username):
    keycloak_client = KeycloakClient()
    return get_user_permissions(keycloak_client, username, project)[0]


@login_required
def view_charge(request, allocation_id):
    charges = []
    alloc = Allocation.objects.get(pk=allocation_id)
    for charge in Charge.objects.filter(allocation__pk=allocation_id):
        used_sus = su_calculators.get_used_sus(charge)
        charge = model_to_dict(charge)
        portal_user = User.objects.get(pk=charge["user"])
        charge["user"] = f"{portal_user.first_name} {portal_user.last_name}"
        charge["user_email"] = portal_user.email
        charge["used_sus"] = used_sus
        charges.append(charge)
    return render(
        request,
        "projects/charge.html",
        {"charges": charges, "balance_service_version": alloc.balance_service_version},
    )
