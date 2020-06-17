from keycloak.realm import KeycloakRealm
from keycloak.admin.users import User, Users
from keycloak.admin.groups import Groups
from keycloak.admin.user.usergroup import UserGroups
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class KeycloakClient:

    def __init__(self):
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm_name = settings.KEYCLOAK_REALM_NAME
        self.client_id = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET

    def _get_token(self, realm):
        openid = realm.open_id_connect(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        return openid.client_credentials()

    def _get_admin_client(self):
        realm = KeycloakRealm(server_url=self.server_url,
                              realm_name='master')
        token = self._get_token(realm)
        admin_client = realm.admin
        admin_client.set_token(token.get('access_token'))
        return admin_client
    
    def _get_group_id_by_name(self, name):
        keycloak_group_id = None
        keycloakproject = Groups(realm_name=self.realm_name,
                                 client=self._get_admin_client())
        
        matching = keycloakproject._client.get(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path('collection', realm=self.realm_name)
            ),
            name=name,
        )
        matching = [u for u in matching if u['name'] == name]
        if matching and len(matching) == 1:
            keycloak_group_id = matching[0]['id']
        
        return keycloak_group_id

    def get_keycloak_user_by_username(self, username):
        keycloakusers = Users(realm_name=self.realm_name,
                              client=self._get_admin_client())
        
        matching = keycloakusers._client.get(
            url=keycloakusers._client.get_full_url(
                keycloakusers.get_path('collection', realm=self.realm_name)
            ),
            username=username,
        )
        matching = [u for u in matching if u['username'] == username]
        if matching and len(matching) == 1:
            return matching[0]
        else:
            return None
    
    def get_user_projects_by_username(self, username):
        user = self.get_keycloak_user_by_username(username)
        if not user:
            return []
        keycloakuser = User(realm_name=self.realm_name, 
                            user_id=user['id'],
                            client=self._get_admin_client())
        
        project_charge_codes = [project['name'] for project in keycloakuser.groups.all()]
        return project_charge_codes
    
    def get_project_members_by_charge_code(self, charge_code):
        project_id = self._get_group_id_by_name(charge_code)
        if not project_id:
            logger.warning('Couldn\'t find project {} in keycloak'.format(charge_code))
            return []
        
        keycloakproject = Groups(realm_name=self.realm_name,
                                 client=self._get_admin_client())
        members = keycloakproject._client.get(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path('collection', realm=self.realm_name)
            ) + '/{id}/members'.format(id=project_id),
        )
        return [m['username'] for m in members]
    
    def update_membership(self, charge_code, username, action):
        user = self.get_keycloak_user_by_username(username)
        project_id = self._get_group_id_by_name(charge_code)
        keycloakusergroups = UserGroups(realm_name=self.realm_name,
                                        user_id=user['id'],
                                        client=self._get_admin_client())
        if action == 'add':
            keycloakusergroups.add(project_id)
        elif action == 'delete':
            keycloakusergroups.delete(project_id)
        else:
            raise ValueError('Unrecognized keycloak membership action')
    
    def create_project(self, charge_code, pi_username):
        keycloakproject = Groups(realm_name=self.realm_name,
                                 client=self._get_admin_client())
        keycloakproject.create(charge_code)
        
        self.update_membership(charge_code, pi_username, 'add')

