from csp.decorators import csp_update
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings
from django.contrib.auth.views import login
from chameleon.keystone_auth import regenerate_tokens
from sharing_portal.conf import JUPYTERHUB_URL

import logging
LOG = logging.getLogger(__name__)

@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    login_return = login(request, current_app=None, extra_context=None)
    password = request.POST.get('password', False)
    if request.user.is_authenticated() and password:
        request.session['is_federated'] = False
        regenerate_tokens(request, password)
    return login_return
