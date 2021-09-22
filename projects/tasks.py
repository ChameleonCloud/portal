import logging

from celery.decorators import task
from django.utils import timezone
from django.core.mail import send_mail
from projects.models import Invitation, Project
from sharing_portal.models import DayPassRequest
from django.contrib.auth.models import User
from util.keycloak_client import KeycloakClient
from .views import get_invitations_beyond_duration
from allocations.models import Allocation

LOG = logging.getLogger(__name__)


@task
def activate_expire_invitations():
    now = timezone.now()

    expired_invitations = Invitation.objects.filter(
        status=Invitation.STATUS_ISSUED, date_expires__lte=now
    )
    expired_invitation_count = 0
    for invitation in expired_invitations:
        charge_code = invitation.project.charge_code
        try:
            invitation.delete()
            expired_invitation_count += 1
        except Exception:
            LOG.exception(
                f"Error expiring invitation with code {invitation.email_address}"
            )
        LOG.info(f"Expired invitation {invitation.email_code} on project {charge_code}")
    LOG.debug(
        "need to expire {} invitations, and {} were actually expired".format(
            len(expired_invitations), expired_invitation_count
        )
    )


@task
def end_daypasses():
    beyond_duration_invitations = get_invitations_beyond_duration()
    for invitation in beyond_duration_invitations:
        try:
            LOG.info(f"Removing user from project with invite {invitation.id}\n")
            project = Project.objects.get(pk=invitation.project_id)
            user = User.objects.get(pk=invitation.user_accepted_id)
            keycloak_client = KeycloakClient()
            keycloak_client.update_membership(
                project.charge_code, user.username, "delete"
            )
            invitation.status = Invitation.STATUS_BEYOND_DURATION
            invitation.save()
        except Exception:
            LOG.error(f"Error ending daypass invite {invitation.id}")

        try:
            # If this invite was on a day pass
            day_pass_request = DayPassRequest.objects.get(invitation=invitation)
            # And there are 10 requests on that same artifact
            approved_requests = DayPassRequest.objects.all().filter(
                artifact=day_pass_request.artifact,
                status = DayPassRequest.STATUS_APPROVED
            ).count()
            if approved_requests == 10:
                # Send an email
                handle_too_many_day_pass_users(day_pass_request.artifact)
        except DayPassRequest.DoesNotExist:
            pass

def handle_too_many_day_pass_users(artifact):
    # Make allocation expire
    allocations = Allocation.objects.filter(status='active', project=artifact.project)
    now = datetime.now(timezone.utc)
    for alloc in allocations:
        alloc.expiration_date=now
        alloc.save()

    subject = f'Pause on day pass requests'
    help_url = request.build_absolute_uri(
        reverse('djangoRT:mytickets')
    )
    body = f"""
    <p>
    Thank you for using our day pass feature for Trovi artifact!
    We have noticied that 10 users have been approved to reproduce
    '{arifact.title}'. As a status check, we have put a pause on the
    allocation in order to request more details. Please submit a ticket to
    our help desk mentioning the situation so we can discuss this further.
    <a href="{help_url}">help desk</a>.
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
        recipient_list=[artifact.project.pi.email],
        message=strip_tags(body),
        html_message=body,
    )


