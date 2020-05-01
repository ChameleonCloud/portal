import requests
from django.conf import settings
import logging
from util.auth.keystone_auth import get_ks_auth_and_session

logger = logging.getLogger('allocations')

class BalanceServiceClient:
    
    def __init__(self):
        if not settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL:
            raise ValueError('Missing ALLOCATIONS_BALANCE_SERVICE_ROOT_URL')

    def call(self, project_code):
        auth, sess = get_ks_auth_and_session()
        headers = auth.get_headers(sess)
        headers['Accept'] = 'application/json'

        url = self.make_url(project_code)
        data = None
        try:
            resp = requests.get(url, headers=headers)
            logger.info('Successfully retrieved balance for project %s', project_code)
            data = resp.json()
            logger.debug('Response from %s: %s', url, data)
        except Exception:
            logger.exception('Failed to retrieve balance for project %s', project_code)

        return data
    
    def recharge(self, project_code, su_allocated):
        auth, sess = get_ks_auth_and_session()
        headers = auth.get_headers(sess)
        headers['Content-Type'] = 'application/json'
        
        url = self.make_url('recharge')
        resp = requests.post(url, headers=headers, json={'project': project_code, 'sus': su_allocated})
        if resp.status_code != 200:
            raise RuntimeError('Balance service recharge failed!')

    def reset(self, project_code):
        auth, sess = get_ks_auth_and_session()
        headers = auth.get_headers(sess)
        headers['Content-Type'] = 'application/json'
        
        url = self.make_url('reset')
        resp = requests.post(url, headers=headers, json={'project': project_code})
        if resp.status_code != 200:
            raise RuntimeError('Balance service reset failed!')

    def make_url(self, route):
        return '{0}/{1}'.format(settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL, route)
