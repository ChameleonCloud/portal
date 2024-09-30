import json
import logging
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import DataError, transaction
from django.forms.models import model_to_dict
from django.http import (Http404, HttpResponseForbidden, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
from keycloak.exceptions import KeycloakClientError

from allocations.models import Allocation, Charge, ChargeBudget
from balance_service.utils import su_calculators
from chameleon.decorators import terms_required
from chameleon.keystone_auth import admin_ks_client
from projects.models import Funding, JoinLink, JoinRequest
from projects.serializer import ProjectExtrasJSONSerializer
from util.keycloak_client import KeycloakClient
from util.project_allocation_mapper import ProjectAllocationMapper

from . import membership
from .forms import (AddBibtexPublicationForm, AllocationCreateForm,
                    ConsentForm, EditNicknameForm, EditPIForm, EditTagForm,
                    FundingFormset, ProjectAddBulkUserForm, ProjectAddUserForm,
                    ProjectCreateForm)
from .models import Invitation, Project, ProjectExtras
from .util import email_exists_on_project, get_charge_code, get_project_members

logger = logging.getLogger("projects")

ROLES = ["Manager", "Member"]


class UserNotPIEligible(Exception):
    pass


class UserPermissions():
    manage: bool
    manage_membership: bool

    def __init__(self, manage, manage_membership):
        self.manage = manage
        self.manage_membership = manage_membership

    @staticmethod
    def _get_user_project_role_scopes(keycloak_client, username, project):
        role, scopes = keycloak_client.get_user_project_role_scopes(
            username, get_charge_code(project)
        )
        logger.info("SCOPES===")
        logger.info(role)
        logger.info(scopes)
        return role, scopes

    @staticmethod
    def _parse_scopes(scopes):
        # NOTE We have these two scopes defined in KC. In implementation,
        # we do not differentiate between them. See our docs for the specifics
        # https://chameleoncloud.readthedocs.io/en/latest/user/project.html#user-roles
        can_manage = "manage" in scopes or "manage-membership" in scopes
        return UserPermissions(
            manage=can_manage,  # Can edit project metadata/allocations
            manage_membership=can_manage,  # Can update members
        )

    @staticmethod
    def get_user_permissions(keycloak_client, username, project):
        _, scopes = UserPermissions._get_user_project_role_scopes(
            keycloak_client, username, project)
        return UserPermissions._parse_scopes(scopes)

    @staticmethod
    def get_manager_projects(keycloak_client, username):
        """Gets project names for all project this user is a manager of
        """
        return [
            project["groupName"]
            for project in keycloak_client.get_user_roles(username)
            if UserPermissions._parse_scopes(project["scopes"]).manage
        ]


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


@login_required
def request_to_join(request, secret):
    try:
        join_link = JoinLink.objects.get(secret=secret)
    except JoinLink.DoesNotExist:
        raise Http404("There is no project for this join link.")

    project = join_link.project
    user = request.user

    if request.POST:
        # User has submitted a response to the project join page
        if join_link.has_join_request(user):
            # If user manages to click the confirm button twice
            messages.error(
                request,
                f"Already sent request to join project {project.charge_code}.",
            )
        elif "confirm_join_project_request" in request.POST:
            # User clicked confirm
            join_request = JoinRequest.objects.create(join_link=join_link, user=user)
            project_url = request.build_absolute_uri(
                reverse("projects:view_project", args=[project.id])
            )
            body = f"""
            <p>{user.email} has requested to join your project, {project.charge_code}.<br>
            Please review all join requests for this project here: <br><br>

            <a href="{project_url}" target="_blank">{project_url}</a><br><br>

            Thanks,<br>
            Chameleon Team
            </p>
            """
            mail_sent = send_mail(
                subject=f"A user has requested to join "
                f"your Chameleon project ({project.charge_code})!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[
                    user.email for user in get_project_membership_managers(project)
                ],
                message=strip_tags(body),
                html_message=body,
            )
            messages.success(
                request,
                f"Your request to join project {project.charge_code} has been sent.",
            )
            if not mail_sent:
                logger.warning(
                    f"Failed to send project join request email ({join_request})"
                )
        return HttpResponseRedirect(reverse("projects:user_projects"))

    # If the user is already a member of the project, just take them to the project page
    if project_member_or_admin_or_superuser(
        user, project, get_project_members(project)
    ):
        messages.success(request, "You are already a member of this project!")
        return HttpResponseRedirect(reverse("projects:view_project", args=[project.id]))

    if join_link.has_join_request(user):
        join_request = join_link.join_requests.get(user=user)
        if join_request.is_accepted():
            # If the user is not a project member, but has an accepted join request,
            # then something went wrong
            messages.error(
                request,
                "Your join request has been accepted, "
                "but you are not a member of this project. "
                "Please reach out to the PI and have them add you manually.",
            )
            return HttpResponseRedirect(reverse("projects:user_projects"))
        elif join_request.is_rejected():
            # If user has been rejected from the project, let them know
            messages.error(
                request,
                f"Your request to join {project.charge_code} "
                f"was rejected by the project's PI.",
            )
            return HttpResponseRedirect(reverse("projects:user_projects"))
        else:
            # If the user hasn't been rejected or accepted, their request is pending
            messages.warning(
                request,
                f"Your request to join project {project.charge_code} is still pending.",
            )
            return HttpResponseRedirect(reverse("projects:user_projects"))

    # If the user is not a member and has no join request,
    return render(
        request, "projects/request_to_join_project.html", {"project": project}
    )


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


def notify_join_request_user(django_request, join_request):
    project = join_request.join_link.project
    link = django_request.build_absolute_uri(
        reverse("projects:view_project", args=[project.id])
    )
    status_str = "accepted!" if join_request.is_accepted() else "rejected."
    subject = (
        f"Your request to join project {project.charge_code} has been {status_str}"
    )
    view_text = (
        f'You can view the project here: <a href="{link}" target="_blank">{link}</a>'
    )
    body = f"""
    {subject} {view_text if join_request.is_accepted() else ''}<br><br>

    Thanks,<br>
    Chameleon Team
    """
    mail_sent = send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[join_request.user.email],
        message=strip_tags(body),
        html_message=body,
    )
    if not mail_sent:
        logger.warning(
            f"Failed to send notification to user for join request {join_request.id}"
        )


def set_budget_for_user_in_project(user, project, target_budget):
    # Creates SU budget for (user, project), deletes budget if target_budget==0
    charge_budget, created = ChargeBudget.objects.get_or_create(
        user=user, project=project
    )
    if target_budget == 0:
        charge_budget.delete()
        return
    charge_budget.su_budget = target_budget
    charge_budget.save()


@login_required
def view_project(request, project_id):
    mapper = ProjectAllocationMapper(request)
    keycloak_client = KeycloakClient()

    try:
        project = mapper.get_project(project_id)
        portal_project = Project.objects.get(id=project.id)
    except Exception as e:
        logger.error(e)
        raise Http404("The requested project does not exist!")

    form = ProjectAddUserForm()
    nickname_form = EditNicknameForm()
    tag_form_args = {"request": request}
    tag_form = EditTagForm(**tag_form_args)
    pubs_form = AddBibtexPublicationForm()
    pi_form = EditPIForm()
    bulk_user_form = ProjectAddBulkUserForm()

    user_roles = keycloak_client.get_roles_for_all_project_members(
        get_charge_code(project)
    )
    users = get_project_members(project)
    if project.active_allocations:
        current_allocation_su_allocated = project.active_allocations[0].computeAllocated
    else:
        current_allocation_su_allocated = 0
    user_permission = UserPermissions.get_user_permissions(
        keycloak_client, request.user.username, project
    )

    # Users list may be stale if we update the membership list
    users_is_stale = False
    if (
        request.POST
        and user_permission.manage_membership
        or is_admin_or_superuser(request.user)
    ):
        form = ProjectAddUserForm()
        if "add_user" in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                users_is_stale = True
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
                users_is_stale = True
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
                if role_name == "manager":
                    # delete user budgets for the user if they are manager
                    user = User.objects.get(username=role_username)
                    try:
                        user_budget = ChargeBudget.objects.get(
                            user=user, project=portal_project
                        )
                    except ChargeBudget.DoesNotExist:
                        # the user does not have a budget created, no-op
                        pass
                    else:
                        user_budget.delete()
            except Exception:
                logger.exception("Failed to change user role")
                messages.error(
                    request,
                    "An unexpected error occurred while attempting "
                    "to change role for this user. Please try again",
                )
        elif "su_budget_user" in request.POST:
            budget_user = User.objects.get(username=request.POST["user_ref"])
            set_budget_for_user_in_project(
                budget_user, portal_project, request.POST["su_budget_user"]
            )
            messages.success(
                request,
                (
                    f"SU budget for user {budget_user.username} "
                    f"is currently set to {request.POST['su_budget_user']}"
                ),
            )
        elif "default_su_budget" in request.POST:
            portal_project.default_su_budget = request.POST["default_su_budget"]
            portal_project.save()
            for u in users:
                u_role = user_roles.get(u.username, "member")
                logger.warning(f"user role is {u_role}, {u}")
                if u_role in ["manager", "admin"]:
                    continue
                set_budget_for_user_in_project(
                    u, portal_project, portal_project.default_su_budget
                )
            messages.success(request, "Updated SU budget for all non-manager users")
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
        elif "accept_join_request" in request.POST:
            try:
                users_is_stale = True
                join_request = JoinRequest.objects.get(
                    id=int(request.POST.get("join_request"))
                )
                user = join_request.user
                if membership.add_user_to_project(project, user.username):
                    join_request.accept()
                    messages.success(
                        request, f"Successfully added {user.username} to this project!"
                    )
                    notify_join_request_user(request, join_request)
                else:
                    messages.error(request, "Failed to add user to project.")
            except KeycloakClientError:
                messages.error(request, "Failed to add user to project.")
            except JoinRequest.DoesNotExist:
                messages.error(request, "Failed to process join request.")
            except DataError:
                messages.error(
                    request,
                    "This join request has already been responded to!",
                )
        elif "reject_join_request" in request.POST:
            try:
                join_request = JoinRequest.objects.get(
                    id=int(request.POST.get("join_request"))
                )
                join_request.reject()
                notify_join_request_user(request, join_request)
            except JoinRequest.DoesNotExist:
                messages.error(request, "Failed to process join request.")
            except DataError:
                messages.error(
                    request, "This join request has already been responded to!"
                )
        elif "nickname" in request.POST:
            nickname_form = edit_nickname(request, project_id)
        elif "tagId" in request.POST:
            tag_form = edit_tag(request, project_id)
        elif "pi_username" in request.POST:
            pi_form = edit_pi(request, project_id)
        elif "add_bulk_users" in request.POST:
            users_is_stale = True
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
        elif "remove_bulk_users" in request.POST:
            users_is_stale = True
            non_managers = [
                user
                for user in get_project_members(project)
                if user_roles.get(user.username) not in ("admin", "manager")
            ]
            errors = []
            for user in non_managers:
                if not membership.remove_user_from_project(project, user):
                    errors.append(f"Failed to remove {user}")
            if not errors:
                messages.success(request, "Removed all non-managers from project.")
            else:
                for error in errors:
                    messages.error(request, error)

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

    if users_is_stale:
        users = get_project_members(project)

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    users_mashup = []
    budget_project = Project.objects.get(charge_code=get_charge_code(project))

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
            try:
                su_budget = ChargeBudget.objects.get(
                    user=portal_user, project=budget_project
                )
            except ChargeBudget.DoesNotExist:
                su_budget_value = current_allocation_su_allocated
            else:
                su_budget_value = su_budget.su_budget
            user["su_budget"] = int(su_budget_value)
            user["su_used"] = su_calculators.calculate_user_total_su_usage(
                portal_user, budget_project
            )
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

    join_link = JoinLink.objects.get_or_create(project_id=project.id)[0]

    is_on_daypass = get_daypass(request.user.id, project_id) is not None

    return render(
        request,
        "projects/view_project.html",
        {
            "project": project,
            "project_nickname": project.nickname,
            "project_tag": project.tag,
            "users": users_mashup,
            "invitations": clean_invitations,
            "join_link": join_link.get_url(request),
            "join_requests": join_link.join_requests.filter(
                status=JoinRequest.Status.PENDING
            ),
            "can_manage_project_membership": user_permission.manage_membership,
            "can_manage_project": user_permission.manage,
            "is_admin": request.user.is_superuser,
            "is_on_daypass": is_on_daypass,
            "form": form,
            "nickname_form": nickname_form,
            "tag_form": tag_form,
            "pi_form": pi_form,
            "pubs_form": pubs_form,
            "bulk_user_form": bulk_user_form,
            "roles": ROLES,
            "host": request.get_host(),
            "su_allocated": current_allocation_su_allocated,
            "project_default_su": portal_project.default_su_budget,
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
            error_messages.append(f"Unable to add user '{user_ref}'. Please try again.")

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
    url = invitation.get_invite_url(request)
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

    project = mapper.get_project(project_id)

    keycloak_client = KeycloakClient()
    user_permission = UserPermissions.get_user_permissions(
        keycloak_client, request.user.username, project
    )
    if not user_permission.manage:
        messages.error(
            request,
            "Only PI Eligible users and Managers can request allocations. If you would "
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
                    project.save()
                    mapper.save_allocation(
                        allocation, project.chargeCode, request.get_host()
                    )
                    new_funding_source = _save_fundings(formset, project_id)
                    _remove_fundings(funding_source, new_funding_source)
                messages.success(request, "Your allocation request has been submitted!")
                return HttpResponseRedirect(
                    reverse("projects:view_project", args=[project.id])
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
            # title, description, tagId
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
    user_permission = UserPermissions.get_user_permissions(
        keycloak_client, request.user.username, project
    )

    if not (user_permission.manage or is_admin_or_superuser(request.user)):
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
def edit_tag(request, project_id):
    form_args = {"request": request}
    project = Project.objects.get(pk=project_id)
    if not request.user.is_superuser and request.user.username != project.pi.username:
        messages.error(request, "Only the PI can update project tag.")
        return EditTagForm(**form_args)

    form = EditTagForm(request.POST, **form_args)
    if form.is_valid(request):
        # try to update type
        try:
            project_tag_id = int(form.cleaned_data["tagId"])
            ProjectAllocationMapper.update_project_tag(project_id, project_tag_id)
            form = EditTagForm(**form_args)
            messages.success(
                request,
                "Update successful! Please refresh the page.",
            )
        except Exception:
            logger.exception("Failed to update project tag")
            messages.error(request, "Failed to update project tag")
    else:
        messages.error(request, "Failed to update project tag")

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
    keycloak_client = KeycloakClient()
    return [
        user for user in users
        if UserPermissions.get_user_permissions(
            keycloak_client, user.username, project).manage_membership
    ]


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
