import requests
from django.conf import settings
import logging
from chameleon.keystone_auth import admin_session

logger = logging.getLogger('allocations')


class BalanceServiceClient:

    def __init__(self):
        if not settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL:
            raise ValueError('Missing ALLOCATIONS_BALANCE_SERVICE_ROOT_URL')

    def _make_headers(self):
        # It doesn't really matter which region we use when generating the
        # authentication token; all the balance service cares about is that
        # it is valid.
        sess = admin_session(settings.OPENSTACK_TACC_REGION)
        headers = sess.session.get_auth_headers()
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'
        return headers

    def call(self, project_code):
        url = self.make_url(project_code)
        data = None
        try:
            resp = requests.get(url, headers=self._make_headers())
            logger.info(
                'Successfully retrieved balance for project %s', project_code)
            data = resp.json()
            logger.debug('Response from %s: %s', url, data)
        except Exception:
            logger.exception(
                'Failed to retrieve balance for project %s', project_code)

        return data

    def recharge(self, project_code, su_allocated):
        url = self.make_url('recharge')
        headers = self._make_headers()
        body = {'project': project_code, 'sus': su_allocated}
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError('Balance service recharge failed!')

    def reset(self, project_code):
        url = self.make_url('reset')
        headers = self._make_headers()
        body = {'project': project_code}
        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError('Balance service reset failed!')

    def make_url(self, route):
        return '{0}/{1}'.format(
            settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL, route)
