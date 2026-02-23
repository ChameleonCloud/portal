from datetime import datetime
from django.contrib.auth import get_user_model
from allocations.models import ChargeBudget
from projects.models import Project
from util.keycloak_client import KeycloakClient, UserAttributes


def add_user_to_project(tas_project, user):
    """Add a user to a Keycloak group representing a Chameleon project.

    If this is the first time the user has been added to any project, also set an
    attribute with the current date indicating when the user joined their first project.

    Also apply the project's default budget to the user

    Args:
        tas_project (pytas.Project): the TAS project representation.
        user (str): the portal user model.
    """
    keycloak_client = KeycloakClient()
    keycloak_client.update_membership(tas_project.chargeCode, user, "add")

    # Check if this is the first time joining an allocation
    kc_user = keycloak_client.get_user_from_portal_user(user)
    if not kc_user["attributes"].get(UserAttributes.LIFECYCLE_ALLOCATION_JOINED):
        keycloak_client.update_user(
            user, lifecycle_allocation_joined=datetime.now()
        )
    # add the project's default budget to the user
    project = Project.objects.get(charge_code=tas_project.chargeCode)
    if project.default_su_budget != 0:
        user_budget = ChargeBudget(
            user=user, project=project, su_budget=project.default_su_budget
        )
        user_budget.save()

    return True


def remove_user_from_project(tas_project, user):
    """Remove a user from a Keycloak group representing a Chameleon project.

    Args:
        tas_project (pytas.Project): the TAS project representation.
        user (str): the portal user model.
    """
    keycloak_client = KeycloakClient()
    keycloak_client.update_membership(tas_project.chargeCode, user, "delete")

    return True
