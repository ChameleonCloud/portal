from keycloak.realm import KeycloakRealm
from keycloak.admin.users import User, Users
from keycloak.admin.groups import Groups
from keycloak.admin.user.usergroup import UserGroups
from keycloak.exceptions import KeycloakClientError
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class KeycloakClient:

    def __init__(self):
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm_name = settings.KEYCLOAK_REALM_NAME
        self.client_id = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET
        self.client_provider_alias = settings.KEYCLOAK_CLIENT_PROVIDER_ALIAS,
        self.client_provider_sub = settings.KEYCLOAK_CLIENT_PROVIDER_SUB,

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

    def _users_admin(self):
        return Users(realm_name=self.realm_name,
                     client=self._get_admin_client())

    def _user_admin(self, user_id):
        return User(realm_name=self.realm_name,
                    user_id=user_id,
                    client=self._get_admin_client())

    def _project_admin(self):
        return Groups(realm_name=self.realm_name,
                      client=self._get_admin_client())

    def _user_projects_admin(self, user_id):
        return UserGroups(realm_name=self.realm_name,
                          user_id=user_id,
                          client=self._get_admin_client())

    def _get_group_id_by_name(self, name):
        keycloak_group_id = None
        keycloakproject = self._project_admin()

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

    def _add_identity(self, user_id, **kwargs):
        keycloakuser = self._user_admin(user_id)
        return keycloakuser._client.post(
            url=keycloakuser._client.get_full_url(
                keycloakuser.get_path('single', realm=self.realm_name, user_id=user_id)
                ) + '/federated-identity/{provider}'.format(provider=self.client_provider_alias),
            data=json.dumps(kwargs, sort_keys=True)
        )

    def get_keycloak_user_by_username(self, username):
        keycloakusers = self._users_admin()

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
        keycloakuser = self._user_admin(user['id'])

        project_charge_codes = [project['name'] for project in keycloakuser.groups.all()]
        return project_charge_codes

    def get_project_members_by_charge_code(self, charge_code):
        project_id = self._get_group_id_by_name(charge_code)
        if not project_id:
            logger.warning('Couldn\'t find project {} in keycloak'.format(charge_code))
            return []

        keycloakproject = self._project_admin()
        members = keycloakproject._client.get(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path('collection', realm=self.realm_name)
            ) + '/{id}/members'.format(id=project_id),
        )
        return [m['username'] for m in members]

    def update_membership(self, charge_code, username, action):
        user = self.get_keycloak_user_by_username(username)
        if not user:
            raise ValueError('User {} does not exist'.format(username))
        project_id = self._get_group_id_by_name(charge_code)
        keycloakusergroups = self._user_projects_admin(user['id'])
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

    def create_user(self, username, first_name=None, last_name=None, email=None,
                    affiliation_title=None, affiliation_department=None,
                    affiliation_institution=None, country=None, citizenship=None, join_date=None):
        try:
            keycloakuser = self._users_admin()
            keycloakuser.create(
                username, first_name=first_name, last_name=last_name, email=email,
                enabled=True, email_verified=True,
                attributes=dict(
                    affiliationTitle=affiliation_title,
                    affiliationDepartment=affiliation_department,
                    affiliationInstitution=affiliation_institution,
                    country=country,
                    citizenship=citizenship,
                    joinDate=join_date
                )
            )
            user = self.get_keycloak_user_by_username(username)
            self._add_identity(
                user_id=user['id'],
                userId=f'f:{self.client_provider_sub}:{username}',
                userName=username
            )
        except KeycloakClientError as err:
            if err.__cause__:
                msg = err.__cause__.response
            else:
                msg = err
            logger.error(f'Failed to create Keycloak user "{username}". Manual '
                         f'cleanup may be required: {msg}')
