import logging

from projects.models import Project
from django.contrib.auth import get_user_model
from util.keycloak_client import KeycloakClient

def get_project_members(project):
    users = []
    # try get members from keycloak
    keycloak_client = KeycloakClient()
    for username in keycloak_client.get_project_members(get_charge_code(project)):
        user = get_user_model().objects.get(username=username)
        if user:
            users.append(user)
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
