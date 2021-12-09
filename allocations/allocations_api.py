import requests
from django.conf import settings
import logging
from chameleon.keystone_auth import admin_session

logger = logging.getLogger("allocations")

# TODO: remove after retiring redis


class BalanceServiceClient:
    def __init__(self):
        if not settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL:
            raise ValueError("Missing ALLOCATIONS_BALANCE_SERVICE_ROOT_URL")

    def _make_headers(self):
        # It doesn't really matter which region we use when generating the
        # authentication token; all the balance service cares about is that
        # it is valid.
        sess = admin_session(settings.OPENSTACK_TACC_REGION)
        headers = sess.session.get_auth_headers()
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        return headers

    def bulk_get_balances(self, project_codes):
        url = self.make_url()
        url += f'?projects={",".join(project_codes)}'
        data = []
        try:
            resp = requests.get(url, headers=self._make_headers())
            data = resp.json()["projects"]
            logger.info(
                "Successfully retrieved balance for projects: %s", project_codes
            )
            logger.debug("Response from %s: %s", url, data)
        except Exception:
            logger.exception(
                "Failed to retrieve balance for projects: %s", project_codes
            )
        return data

    def get_balance(self, project_code):
        res = self.bulk_get_balances([project_code])
        if not res:
            raise RuntimeError(f"No balances returned for {project_code}")
        return res[0]

    def recharge(self, project_code, su_allocated):
        url = self.make_url("recharge")
        headers = self._make_headers()
        body = {"project": project_code, "sus": su_allocated}
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError("Balance service recharge failed!")

    def reset(self, project_code):
        url = self.make_url("reset")
        headers = self._make_headers()
        body = {"project": project_code}
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError("Balance service reset failed!")

    def check_create(self, data):
        url = self.make_url("v1/check-create")
        headers = self._make_headers()
        return requests.post(url, headers=headers, json=data)

    def check_update(self, data):
        url = self.make_url("v1/check-update")
        headers = self._make_headers()
        return requests.post(url, headers=headers, json=data)

    def on_end(self, data):
        url = self.make_url("v1/on-end")
        headers = self._make_headers()
        return requests.post(url, headers=headers, json=data)

    def make_url(self, route=None):
        url = settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL
        if route:
            url += "/" + route
        return url
