import logging
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from chameleon.models import KeycloakUser
from util.keycloak_client import KeycloakClient

logger = logging.getLogger("projects.util")


def get_user_by_reference(keycloak_id=None, username=None, email=None):
    """
    Returns a Django User model given a Keycloak user reference,
    prioritizing keycloak_id, then username, then email.

    Args:
        keycloak_id (str): The Keycloak user ID.
        username (str): The Keycloak username.
        email (str): The Keycloak email address.

    Returns:
        User: The Django User model if found, otherwise None.
    """
    if keycloak_id:
        try:
            keycloak_user = KeycloakUser.objects.get(sub=keycloak_id)
            return keycloak_user.user
        except KeycloakUser.DoesNotExist:
            logger.warning(f"Could not find KeycloakUser with sub={keycloak_id}")
    if username:
        u = get_user_model().objects.filter(username__iexact=username).first()
        if u:
            return u
    if email:
        u = get_user_model().objects.filter(email__iexact=email).first()
        if u:
            return u
    return None


def get_project_members(project):
    keycloak_client = KeycloakClient()
    charge_code = get_charge_code(project)

    users = []
    for kc_user in keycloak_client.get_project_members(charge_code):
        # match KC user by ID, then username, then email
        user = get_user_by_reference(
            keycloak_id=kc_user["id"], username=kc_user["username"], email=kc_user["email"]
        )
        if user:
            users.append(user)
        else:
            logger.warning(f"Could not get user model for Keycloak user {kc_user['id']}")

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
