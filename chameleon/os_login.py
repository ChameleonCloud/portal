from csp.decorators import csp_update
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import login, logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from chameleon.keystone_auth import regenerate_tokens
from util.project_allocation_mapper import ProjectAllocationMapper

import logging
LOG = logging.getLogger(__name__)

@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    if request.GET.get(settings.FORCE_OLD_LOGIN_EXPERIENCE_PARAM) != '1':
        return HttpResponseRedirect(reverse('oidc_authentication_init'))

    login_return = login(request, current_app=None, extra_context=None)
    password = request.POST.get('password', False)
    if request.user.is_authenticated() and password:
        request.session['is_federated'] = False
        regenerate_tokens(request, password)
        mapper = ProjectAllocationMapper(request)
        mapper.lazy_add_user_to_keycloak()
    return login_return


@csrf_protect
@never_cache
def custom_logout(request):
    # TODO(jason): once we drop support for password login, we can delete this
    # custom logout function in favor of using the OIDC_OP_LOGOUT_URL_METHOD
    # setting in the oidc module.
    logout_redirect_url = settings.LOGOUT_REDIRECT_URL
    if (request.user.is_authenticated() and
        request.session.get('is_federated') and logout_redirect_url):
        auth_logout(request)
        return HttpResponseRedirect(logout_redirect_url)

    return logout(request, next_page='/')
