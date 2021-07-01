import logging

from celery.decorators import task
from django.utils import timezone
from projects.models import Invitation

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
