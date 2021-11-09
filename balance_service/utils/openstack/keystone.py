import logging
import requests

from django.conf import settings

from balance_service import exceptions

LOG = logging.getLogger(__name__)


class KeystoneAPI:
    def __init__(self, token, auth_url):
        self.auth_url = self.verify_auth_url(auth_url)

        self.token = token
        self.headers = {"X-Auth-Token": self.token, "Content-Type": "application/json"}

    @classmethod
    def load_from_request(cls, request):
        keystone_auth_token = request.headers.get("X-Auth-Token")

        try:
            context = request.json.get("context", {})
            auth_url = context.get("auth_url")
        except Exception:
            auth_url = None

        return cls(keystone_auth_token, auth_url=auth_url)

    def verify_auth_url(self, auth_url):
        allowed_auth_urls = [
            settings.OPENSTACK_TACC_AUTH_URL,
            settings.OPENSTACK_UC_AUTH_URL,
        ]

        auth_url.rstrip("/")

        if auth_url[-3:] != "/v3":
            auth_url += "/v3"

        if auth_url not in allowed_auth_urls:
            raise exceptions.AuthURLException(auth_url)

        return auth_url

    def get_auth_username(self):
        if not self.token:
            raise exceptions.MissingAuthInformation()

        auth_users = settings.ALLOWED_OPENSTACK_SERVICE_USERS
        url = "{}/auth/tokens".format(self.auth_url)
        data = {
            "auth": {"identity": {"methods": ["token"], "token": {"id": self.token}}}
        }

        resp = requests.post(url, headers=self.headers, json=data)

        if resp.status_code in [200, 201]:
            user_name = resp.json()["token"]["user"]["name"]
            if user_name not in auth_users:
                raise exceptions.AuthUserException(user_name)

            return user_name
        else:
            resp.raise_for_status()

    def get_project(self, project_id):
        url = "{}/projects/{}".format(self.auth_url, project_id)
        res = requests.get(url, headers=self.headers)
        res_json = res.json()
        LOG.debug(f"Fetched project from Keystone: {res_json}")
        return res_json.get("project")

    def get_user(self, user_id):
        url = "{}/users/{}".format(self.auth_url, user_id)
        res = requests.get(url, headers=self.headers)
        res_json = res.json()
        LOG.debug(f"Fetched user from Keystone: {res_json}")
        return res_json.get("user")
