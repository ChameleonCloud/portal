from csp.decorators import csp_update
from django.conf import settings
from django.contrib.auth.views import login
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from chameleon.keystone_auth import regenerate_tokens

import logging
LOG = logging.getLogger(__name__)

@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    if request.COOKIES.get(settings.NEW_LOGIN_EXPERIENCE_COOKIE) == '1':
        return HttpResponseRedirect(reverse('oidc_authentication_init'))

    login_return = login(request, current_app=None, extra_context=None)
    password = request.POST.get('password', False)
    if request.user.is_authenticated() and password:
        request.session['is_federated'] = False
        regenerate_tokens(request, password)
    return login_return
