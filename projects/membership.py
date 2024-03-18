from datetime import datetime
from django.contrib.auth import get_user_model
from allocations.models import ChargeBudget
from projects.models import Project
from util.keycloak_client import KeycloakClient, UserAttributes


def get_user(user_ref):
    """Look up a user given a username OR an email address.

    Args:
        user_ref (str): the username or email address to look up.

    Returns: the UserModel instance corresponding to the user.

    Raises:
        UserModel.DoesNotExist: if the user cannot be found.
    """
    UserModel = get_user_model()
    try:
        return UserModel.objects.get(username=user_ref)
    except UserModel.DoesNotExist:
        return UserModel.objects.get(email=user_ref)


def add_user_to_project(tas_project, user_ref):
    """Add a user to a Keycloak group representing a Chameleon project.

    If this is the first time the user has been added to any project, also set an
    attribute with the current date indicating when the user joined their first project.

    Also apply the project's default budget to the user

    Args:
        tas_project (pytas.Project): the TAS project representation.
        user_ref (str): the username or email address of the user.
    """
    keycloak_client = KeycloakClient()
    user = get_user(user_ref)
    keycloak_client.update_membership(tas_project.chargeCode, user.username, "add")

    # Check if this is the first time joining an allocation
    kc_user = keycloak_client.get_user_by_username(user.username)
    if not kc_user["attributes"].get(UserAttributes.LIFECYCLE_ALLOCATION_JOINED):
        keycloak_client.update_user(
            user.username, lifecycle_allocation_joined=datetime.now()
        )
    # add the project's default budget to the user
    project = Project.objects.get(charge_code=tas_project.chargeCode)
    if project.default_su_budget != 0:
        user_budget = ChargeBudget(
            user=user, project=project, su_budget=project.default_su_budget
        )
        user_budget.save()

    return True


def remove_user_from_project(tas_project, user_ref):
    """Remove a user from a Keycloak group representing a Chameleon project.

    Args:
        tas_project (pytas.Project): the TAS project representation.
        user_ref (str): the username or email address of the user.
    """
    keycloak_client = KeycloakClient()
    user = get_user(user_ref)
    keycloak_client.update_membership(tas_project.chargeCode, user.username, "delete")

    return True
