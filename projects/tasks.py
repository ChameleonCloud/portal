import logging

from celery.decorators import task
from django.utils import timezone
from projects.models import Invitation, Project
from django.contrib.auth.models import User
from util.keycloak_client import KeycloakClient
import .util as util

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
    now = timezone.now()

    past_duration_invitations = util.get_invitations_past_duration()
    for invitation in past_duration_invitations:
        try:
            LOG.info(f"Removing user from project with invite {invitation.id}\n")
            project = Project.objects.get(pk=invitation.project_id)
            user = User.objects.get(pk=invitation.user_accepted_id)
            keycloak_client = KeycloakClient()
            keycloak_client.update_membership(project.charge_code, user.username, "delete")
            invite.status = Invitation.STATUS_PAST_DURATION
            invite.save()
        except Exception:
            LOG.error(f"Error ending daypass invite {invitation.id}")
