from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings
from django.contrib.auth.views import login
import sys
from keystoneclient import client as ks_client
from keystoneauth1.exceptions.http import NotFound as NotFoundException

import logging

logger = logging.getLogger(__name__)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    login_return = login(request, current_app=None, extra_context=None)

    if request.user.is_authenticated() and request.POST.get('password', False):
        set_unscoped_token(request)

    return login_return

def set_unscoped_token(request):
    try:
        unscoped_token = ks_client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL + 'abcdefg').get_raw_token_from_identity_service( \
            auth_url=settings.OPENSTACK_KEYSTONE_URL,username=request.POST.get('username'), password=request.POST.get('password'), project_id=None, \
            user_domain_name='default', user_domain_id='default')
        request.session['unscoped_token'] = unscoped_token
        logger.info('***Unscoped Token retrieved and stored in session for user: ' + request.POST.get('username'))
    except NotFoundException as nfe:
        try:
            logger.error('Error retrieving Openstack Token: {}'.format(nfe.message) + str(sys.exc_info()[0]))
            unscoped_token = ks_client.Client(auth_url=settings.OPENSTACK_ALT_KEYSTONE_URL).get_raw_token_from_identity_service( \
                auth_url=settings.OPENSTACK_ALT_KEYSTONE_URL,username=request.POST.get('username'), password=request.POST.get('password'), project_id=None, \
                user_domain_name='default', user_domain_id='default')
            request.session['unscoped_token'] = unscoped_token
            logger.info('***Unscoped Token retrieved from OPENSTACK_ALT_KEYSTONE_URL and stored in session for user: ' + request.POST.get('username'))
        except Exception as err2:
            logger.error('Error retrieving Openstack Token from OPENSTACK_ALT_KEYSTONE_URL: {}'.format(err2.message) + str(sys.exc_info()[0]))
    except Exception as err:
        logger.error('Error retrieving Openstack Token: {}'.format(err.message) + str(sys.exc_info()[0]))