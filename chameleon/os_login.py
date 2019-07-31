from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings
from django.contrib.auth.views import login
import sys
from keystoneclient import client as ks_client
from keystoneclient.v3 import client as v3_ksclient
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneauth1.exceptions.http import NotFound as NotFoundException
import time
import logging

logger = logging.getLogger(__name__)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    login_return = login(request, current_app=None, extra_context=None)
    if request.user.is_authenticated() and request.POST.get('password', False):
        get_unscoped_token(request)
    return login_return

def get_unscoped_token(request):
    update_ks_password(request)
    time.sleep(1) ## giving keystone a second to catch-up, saw intermittent issues getting tokens without this
    un = request.POST.get('username')
    pw = request.POST.get('password')
    auth_urls = [settings.OPENSTACK_KEYSTONE_URL, settings.OPENSTACK_ALT_KEYSTONE_URL]
    for auth_url in auth_urls:
        try:
            auth = v3.Password(auth_url=auth_url,username=un, password=pw, user_domain_name='default', unscoped=True)
            sess = session.Session(auth=auth, timeout=5)
            unscoped_token = {'auth_token':auth.get_auth_ref(sess).auth_token}
            request.session['unscoped_token'] = unscoped_token
            logger.info('***Unscoped Token retrieved and stored in session for user: ' + request.POST.get('username'))
            return unscoped_token
        except Exception as e:
            logger.error('Error retrieving Openstack Token from KEYSTONE_URL: {}'.format(auth_url + ', ' + e.message) + str(sys.exc_info()[0]))
    return None

'''
    Update keystone with tas-verified password
'''
def update_ks_password(request):
    try:
        logger.info('Synchronizing password to keystone for user: ' + request.POST.get('username'))
        auth = v3.Password(auth_url=settings.OPENSTACK_KEYSTONE_URL,username=settings.OPENSTACK_SERVICE_USERNAME, password=settings.OPENSTACK_SERVICE_PASSWORD, \
            project_id=settings.OPENSTACK_SERVICE_PROJECT_ID, project_name='services', user_domain_id="default")
        sess = session.Session(auth=auth, timeout=5)
        ks = v3_ksclient.Client(session=sess, region_name=settings.OPENSTACK_TACC_REGION)
        user = filter(lambda this: this.name==request.POST.get('username'), ks.users.list())
        if user:
            ks.users.update(user=user[0], password=request.POST.get('password'))
            logger.info('Password sync to keystone successful for user: ' + request.POST.get('username'))
        else:
            logger.info('User not found in keystone: ' + request.POST.get('username'))
    except Exception as e:
        logger.error('Error synchronizing password to keystone for user: {}'.format(request.POST.get('username') + ': ' + e.message) + str(sys.exc_info()[0]))