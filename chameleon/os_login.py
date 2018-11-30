from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings
from django.contrib.auth.views import login

from keystoneclient import client as ks_client

import logging

logger = logging.getLogger(__name__)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request,
          current_app=None, extra_context=None):
    login_return = login(request,
    current_app=None, extra_context=None)
    logger.error('is user logged in: ' + str(request.user.is_authenticated()))
    if request.user.is_authenticated() and request.POST.get('password', False):
        unscoped_token = ks_client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL).get_raw_token_from_identity_service( \
            auth_url=settings.OPENSTACK_KEYSTONE_URL,username=request.POST.get('username'), password=request.POST.get('password'), project_id=None, \
            user_domain_name='default', user_domain_id='default')
        request.session['unscoped_token'] = unscoped_token
        logger.error('*********************################## Unscoped Toke: ' + str(request.session['unscoped_token']))
    return login_return
