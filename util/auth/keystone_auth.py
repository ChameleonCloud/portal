from keystoneauth1.identity import v3
from keystoneauth1 import adapter, session
from django.conf import settings

def get_ks_auth_and_session():
    auth = v3.Password(auth_url=settings.OPENSTACK_KEYSTONE_URL,username=settings.OPENSTACK_SERVICE_USERNAME, \
        password=settings.OPENSTACK_SERVICE_PASSWORD, \
        project_id=settings.OPENSTACK_SERVICE_PROJECT_ID, project_name='services', user_domain_id="default")
    sess = session.Session(auth=auth, timeout=5)
    return auth, sess
