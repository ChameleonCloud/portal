from projects.models import Project
from django.contrib.auth import get_user_model
from util.keycloak_client import KeycloakClient

def get_project_members(project):
    users = []
    # try get members from keycloak
    keycloak_client = KeycloakClient()
    for username in keycloak_client.get_project_members(project.chargeCode):
        user = get_user_model().objects.get(username=username)
        if user:
            users.append(user)
    return users


def email_exists_on_project(project_id, email_address):
    project = Project.objects.get(pk=project_id)
    for member in get_project_members(project):
        if email_address == member.email:
            return True
    return False

