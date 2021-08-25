import logging

from django.contrib.auth import get_user_model
from util.keycloak_client import KeycloakClient
from .models import Invitation

logger = logging.getLogger("projects.util")


def get_project_members(project):
    users = []
    # try get members from keycloak
    keycloak_client = KeycloakClient()
    for username in keycloak_client.get_project_members(get_charge_code(project)):
        try:
            user = get_user_model().objects.get(username=username)
            users.append(user)
        except get_user_model().DoesNotExist:
            logger.exception(f"Could not get user model for {username}")
    return users


def email_exists_on_project(project, email_address):
    for member in get_project_members(project):
        if email_address == member.email:
            return True
    return False


# Sometimes the project is pytas, sometimes its a Django Model. This tries
# to determine which should be used.
def get_charge_code(project):
    if hasattr(project, "charge_code"):
        return project.charge_code
    if hasattr(project, "chargeCode"):
        return project.chargeCode
    raise AttributeError("project has no known charge code attribute")

def get_invitations_past_duration():
    return Invitation.objects.raw(
        f'SELECT * FROM projects_invitation WHERE status = \'{Invitation.STATUS_ACCEPTED}\' AND DATE_ADD(date_accepted, INTERVAL duration HOUR) < NOW()'
    )

def get_daypass_time_left(user_id, project_id):
    rqs = Invitation.objects.raw(
        f'SELECT id, TIMEDIFF(DATE_ADD(date_accepted, INTERVAL duration HOUR), NOW()) AS timeleft FROM projects_invitation WHERE status = \'{Invitation.STATUS_ACCEPTED}\' AND DATE_ADD(date_accepted, INTERVAL duration HOUR) > NOW() AND user_accepted_id = {user_id} AND project_id = {project_id} LIMIT 1'
    )
    for row in rqs:
        return row.timeleft
    return None
