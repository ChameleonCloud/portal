from datetime import datetime, timezone
from django.contrib.auth import get_user_model
from allocations.models import ChargeBudget
from projects.models import Project
from util.keycloak_client import KeycloakClient, UserAttributes
import logging

LOG = logging.getLogger(__name__)


def append_project_membership_event(
    kc_user, charge_code, event_type, check_duplicates=False
):
    """Append a project membership event to the Keycloak user's attributes.

    Args:
        kc_user (dict): The Keycloak user dict.
        charge_code (str): The charge code of the project.
        event_type (str): The type of event ("add" or "remove"). For backdated events, there is also "add_backdate".
        check_duplicates (bool): If True, check for existing events with the same charge code and event type before appending. Defaults to False.
    """
    attr = kc_user["attributes"].get(UserAttributes.GROUP_EVENTS) or []
    # Events can either by a list or string. If it's a string, convert to list for appending.
    # It is a string when there is just one event.
    if isinstance(attr, str):
        attr = [attr]

    if check_duplicates:
        for event in attr:
            e_charge_code, e_event_type, e_timestamp = event.split(",")
            if e_charge_code == charge_code and e_event_type == event_type:
                LOG.warning(
                    f"Duplicate event for user {kc_user['username']}: {event_type} {charge_code} already exists in {attr}"
                )
                return attr
    attr.append(f"{charge_code},{event_type},{datetime.now(timezone.utc).isoformat()}")
    return attr


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
    update_args = {}
    # Check if this is the first time joining an allocation
    kc_user = keycloak_client.get_user_from_portal_user(user)
    if not kc_user["attributes"].get(UserAttributes.LIFECYCLE_ALLOCATION_JOINED):
        update_args["lifecycle_allocation_joined"] = datetime.now()

    # Update UserAttributes.GROUP_EVENTS with an entry for this event
    update_args["group_events"] = append_project_membership_event(
        kc_user, tas_project.chargeCode, "add"
    )

    keycloak_client.update_user(user, **update_args)

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

    kc_user = keycloak_client.get_user_from_portal_user(user)
    update_args = {}
    update_args["group_events"] = append_project_membership_event(
        kc_user, tas_project.chargeCode, "remove"
    )
    keycloak_client.update_user(user, **update_args)

    return True
