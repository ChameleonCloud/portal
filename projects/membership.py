from django.contrib.auth import get_user_model
from util.keycloak_client import KeycloakClient


def _update_user_membership(tas_project, user_ref, action=None):
    if action not in ["add", "delete"]:
        raise ValueError("Invalid membership action {}".format(action))

    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(username=user_ref)
    except UserModel.DoesNotExist:
        user = UserModel.objects.get(email=user_ref)

    charge_code = tas_project.chargeCode
    keycloak_client = KeycloakClient()
    keycloak_client.update_membership(charge_code, user.username, action)
    return True


def add_user_to_project(tas_project, user_ref):
    return _update_user_membership(tas_project, user_ref, action="add")


def remove_user_from_project(tas_project, user_ref):
    return _update_user_membership(tas_project, user_ref, action="delete")
