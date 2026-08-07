from csp.decorators import csp_update
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

import logging

LOG = logging.getLogger(__name__)


@csp_update({"frame-ancestors": [settings.ARTIFACT_SHARING_JUPYTERHUB_URL]})
@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    base_path = reverse("oidc_authentication_init")
    # Preserve the next redirect if it exists
    if "next" in request.GET:
        next_path = request.GET["next"]
        redir_path = f"{base_path}?next={next_path}"
        return HttpResponseRedirect(redir_path)
    return HttpResponseRedirect(base_path)


@csrf_protect
@never_cache
def custom_logout(request):
    logout_redirect_url = settings.LOGOUT_REDIRECT_URL
    auth_logout(request)
    return HttpResponseRedirect(logout_redirect_url)


