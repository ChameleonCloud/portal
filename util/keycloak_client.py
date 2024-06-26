import json
import logging
from datetime import datetime, timezone

from django.conf import settings
from keycloak.admin.groups import Groups
from keycloak.admin.user.usergroup import UserGroups
from keycloak.admin.user.usergrouproles import UserGroupRoles
from keycloak.admin.users import User, Users
from keycloak.exceptions import KeycloakClientError
from keycloak.realm import KeycloakRealm

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class UserAttributes:
    LIFECYCLE_ALLOCATION_JOINED = "lifecycleAllocationJoined"


class DuplicateUserError(Exception):
    pass


class KeycloakClient:
    def __init__(self):
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm_name = settings.KEYCLOAK_REALM_NAME
        self.client_id = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET
        self.client_provider_alias = (settings.KEYCLOAK_CLIENT_PROVIDER_ALIAS,)
        self.client_provider_sub = (settings.KEYCLOAK_CLIENT_PROVIDER_SUB,)

    def _get_token(self, realm):
        openid = realm.open_id_connect(
            client_id=self.client_id, client_secret=self.client_secret
        )
        return openid.client_credentials()

    def _get_admin_client(self):
        realm = KeycloakRealm(server_url=self.server_url, realm_name="master")
        token = self._get_token(realm)
        admin_client = realm.admin
        admin_client.set_token(token.get("access_token"))
        return admin_client

    def _users_admin(self):
        return Users(realm_name=self.realm_name, client=self._get_admin_client())

    def _user_admin(self, user_id):
        return User(
            realm_name=self.realm_name, user_id=user_id, client=self._get_admin_client()
        )

    def _project_admin(self):
        return Groups(realm_name=self.realm_name, client=self._get_admin_client())

    def _user_projects_admin(self, user_id):
        return UserGroups(
            realm_name=self.realm_name, user_id=user_id, client=self._get_admin_client()
        )

    def _user_project_roles_admin(self, user_id):
        return UserGroupRoles(
            realm_name=self.realm_name, user_id=user_id, client=self._get_admin_client()
        )

    def _lookup_group(self, name):
        keycloakproject = self._project_admin()

        matching = [
            u
            for u in keycloakproject._client.get(
                url=keycloakproject._client.get_full_url(
                    keycloakproject.get_path("collection", realm=self.realm_name)
                ),
                briefRepresentation=False,
            )
            if u["name"] == name
        ]
        return next(iter(matching), None)

    def _add_identity(self, user_id, **kwargs):
        keycloakuser = self._user_admin(user_id)
        return keycloakuser._client.post(
            url=keycloakuser._client.get_full_url(
                keycloakuser.get_path("single", realm=self.realm_name, user_id=user_id)
            )
            + "/federated-identity/{provider}".format(
                provider=self.client_provider_alias
            ),
            data=json.dumps(kwargs, sort_keys=True),
        )

    def get_user_by_username(self, username):
        keycloakusers = self._users_admin()

        matching = keycloakusers._client.get(
            url=keycloakusers._client.get_full_url(
                keycloakusers.get_path("collection", realm=self.realm_name)
            ),
            username=username,
        )
        matching = [u for u in matching if u["username"] == username]
        if matching and len(matching) == 1:
            user = matching[0]
            # normalize attributes
            for key, val in user["attributes"].items():
                if type(val) is list and len(val) == 1:
                    user["attributes"][key] = val[0]
            return user
        else:
            return None

    def get_all_users_attributes(self):
        keycloakusers = self._users_admin()

        result = {}
        for user in keycloakusers.all(max_results=-1):
            result[user["username"]] = user.get("attributes")

        return result

    def get_user_projects_by_username(self, username):
        user = self.get_user_by_username(username)
        if not user:
            return []
        keycloakuser = self._user_admin(user["id"])

        project_charge_codes = [
            project["name"] for project in keycloakuser.groups.all()
        ]
        return project_charge_codes

    def get_full_user_projects_by_username(self, username):
        user = self.get_user_by_username(username)
        if not user:
            return []
        keycloakuser = self._user_admin(user["id"])
        projects = [project for project in keycloakuser.groups.all()]
        return projects

    def get_project_members(self, charge_code):
        group = self._lookup_group(charge_code)
        if not group:
            logger.warning("Couldn't find group {} in keycloak".format(charge_code))
            return []

        keycloakproject = self._project_admin()
        members = keycloakproject._client.get(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path("collection", realm=self.realm_name)
            )
            + "/{id}/members?max=9999".format(id=group["id"]),
        )
        return [m["username"] for m in members]

    def update_membership(self, charge_code, username, action):
        user = self.get_user_by_username(username)
        if not user:
            raise ValueError(f"User {username} does not exist")
        group = self._lookup_group(charge_code)
        if not group:
            raise ValueError(f"Group {charge_code} does not exist")
        group_id = group["id"]
        keycloakusergroups = self._user_projects_admin(user["id"])
        if action == "add":
            keycloakusergroups.add(group_id)
        elif action == "delete":
            keycloakusergroups.delete(group_id)
            for sub_group in group["subGroups"]:
                keycloakusergroups.delete(sub_group["id"])
        else:
            raise ValueError("Unrecognized keycloak membership action")

    def create_project(self, charge_code, pi_username):
        keycloakproject = Groups(
            realm_name=self.realm_name, client=self._get_admin_client()
        )
        keycloakproject.create(charge_code)

        self.update_membership(charge_code, pi_username, "add")
        self.set_user_project_role(pi_username, charge_code, "admin")

    def delete_project(self, charge_code):
        group = self._lookup_group(charge_code)
        if not group:
            logger.warning("Couldn't find group {} in keycloak".format(charge_code))
            return

        keycloakproject = self._project_admin()
        keycloakproject._client.delete(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path("collection", realm=self.realm_name)
            )
            + "/{id}".format(id=group["id"]),
        )

    def update_project(self, charge_code, **group_attributes):
        group = self._lookup_group(charge_code)
        if not group:
            raise ValueError(f"Group {charge_code} does not exist")
        # Ensure all attributes are wrapped in lists
        group_attributes = {
            k: (v if isinstance(v, list) else [v]) for k, v in group_attributes.items()
        }
        # Avoid nulling out existing values (PATCH not supported)
        for k, v in group.get("attributes", {}).items():
            group_attributes.setdefault(k, v)
        keycloakproject = Groups(
            realm_name=self.realm_name, client=self._get_admin_client()
        )
        keycloakproject._client.put(
            url=keycloakproject._client.get_full_url(
                keycloakproject.get_path("collection", realm=self.realm_name)
            )
            + "/{id}".format(id=group["id"]),
            data=json.dumps(
                {"attributes": group_attributes, "name": charge_code},
                sort_keys=True,
            ),
        )

    def create_user(
        self,
        username,
        first_name=None,
        last_name=None,
        email=None,
        affiliation_title=None,
        affiliation_department=None,
        affiliation_institution=None,
        country=None,
        citizenship=None,
        join_date=None,
    ):
        try:
            keycloakuser = self._users_admin()
            keycloakuser.create(
                username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                enabled=True,
                email_verified=True,
                attributes=dict(
                    affiliationTitle=affiliation_title,
                    affiliationDepartment=affiliation_department,
                    affiliationInstitution=affiliation_institution,
                    country=country,
                    citizenship=citizenship,
                    joinDate=join_date,
                ),
            )
            user = self.get_user_by_username(username)
            self._add_identity(
                user_id=user["id"],
                userId=f"f:{self.client_provider_sub}:{username}",
                userName=username,
            )
        except KeycloakClientError as err:
            if err.__cause__:
                msg = err.__cause__.response
            else:
                msg = err
            logger.error(
                f'Failed to create Keycloak user "{username}". Manual '
                f"cleanup may be required: {msg}"
            )

    def update_user(
        self,
        username,
        email=None,
        affiliation_title=None,
        affiliation_department=None,
        affiliation_institution=None,
        country=None,
        citizenship=None,
        phone=None,
        lifecycle_allocation_joined: "datetime" = None,
    ):
        user = self.get_user_by_username(username)
        if not user:
            raise ValueError(f"Couldn't find user {username}")
        kc_user = self._user_admin(user["id"])

        update_attrs = kc_user.user.get("attributes", {}).copy()
        if affiliation_title is not None:
            update_attrs["affiliationTitle"] = affiliation_title
        if affiliation_department is not None:
            update_attrs["affiliationDepartment"] = affiliation_department
        if affiliation_institution is not None:
            update_attrs["affiliationInstitution"] = affiliation_institution
        if country is not None:
            update_attrs["country"] = country
        if citizenship is not None:
            update_attrs["citizenship"] = citizenship
        if phone is not None:
            update_attrs["phone"] = phone
        if lifecycle_allocation_joined is not None:
            dt = lifecycle_allocation_joined.astimezone(timezone.utc)
            update_attrs[UserAttributes.LIFECYCLE_ALLOCATION_JOINED] = dt.strftime(
                DATETIME_FORMAT
            )

        update_kwargs = {"attributes": update_attrs}
        if email is not None:
            update_kwargs["email"] = email

        try:
            kc_user.update(**update_kwargs)
        except KeycloakClientError as err:
            res = getattr(err.original_exc, "response", None)
            if res is not None and (res.status_code == 409):
                raise DuplicateUserError()
            else:
                raise

    def get_user_roles(self, username):
        user = self.get_user_by_username(username)
        if not user:
            raise ValueError(f"Couldn't find user {username}")
        keycloakusergrouproles = self._user_project_roles_admin(user["id"])

        return keycloakusergrouproles.all()

    def get_user_project_role_scopes(self, username, project_charge_code):
        user = self.get_user_by_username(username)
        if not user:
            raise ValueError(f"Couldn't find user {username}")
        group = self._lookup_group(project_charge_code)
        if not group:
            raise ValueError(f"Couldn't find project {project_charge_code}")
        keycloakusergrouproles = self._user_project_roles_admin(user["id"])

        role_scopes = next(iter(keycloakusergrouproles.by_group_id(group["id"])), None)
        if role_scopes:
            return role_scopes["policy"], role_scopes["scopes"]

        return None, []

    def set_user_project_role(self, username, project_charge_code, role):
        user = self.get_user_by_username(username)
        if not user:
            raise ValueError(f"Couldn't find user {username}")
        keycloakusergrouproles = self._user_project_roles_admin(user["id"])

        keycloakusergrouproles.grant(policy=role, group_name=project_charge_code)

    def get_roles_for_all_project_members(self, project_charge_code):
        group = self._lookup_group(project_charge_code)
        if not group:
            raise ValueError(f"Couldn't find project {project_charge_code}")
        keycloakusergrouproles = self._user_project_roles_admin(None)

        return keycloakusergrouproles.bulk_fetch_group_member_roles(group["id"])
