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

    def make_url(self, project_code):
        return '{0}/{1}'.format(settings.ALLOCATIONS_BALANCE_SERVICE_ROOT_URL, project_code)
