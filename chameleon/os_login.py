from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from pytas.http import TASClient

from chameleon.keystone_auth import has_valid_token, regenerate_tokens
from util.project_allocation_mapper import ProjectAllocationMapper

import logging

LOG = logging.getLogger(__name__)


@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
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


@login_required
@sensitive_post_parameters()
@csrf_protect
@never_cache
def confirm_legacy_credentials(request):
    error_message = (
        "Your legacy credentials were rejected. Click "
        f'<a href="{reverse("federation_migrate_account")}?force=1">here</a> '
        "to skip this step. Some aspects of your old account may not be "
        "migratable without valid legacy credentials."
    )
    if request.method == "POST":
        form = KSAuthForm(request, data=request.POST)
        username = request.POST.get("username")
        password = request.POST.get("password")
        if request.user.username == username and form.is_valid():
            tas = TASClient()
            if tas.authenticate(username, password):
                regenerate_tokens(request, password)
                # Check if we were able to generate a token for the region the
                # user is trying to log in to
                if has_valid_token(request, region=request.GET.get("region")):
                    LOG.info(
                        (
                            "User {} retrieved unscoped token successfully via manual "
                            "form.".format(username)
                        )
                    )
                else:
                    LOG.info(
                        (
                            "User {} could not retrieve unscoped token via manual "
                            "form.".format(username)
                        )
                    )
                    # Keystone failed for some reason
                    messages.error(request, error_message)
            else:
                # Invalid password
                messages.error(request, error_message)
        else:
            LOG.error(
                "An error occurred on form validation for user " + request.user.username
            )
            messages.error(request, error_message)
        return redirect(request.GET.get("next"))

    form = KSAuthForm(request)

    return render(request, "federation/confirm_legacy_credentials.html", {"form": form})


class KSAuthForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        if request is not None:
            username = request.user.username
            initial = kwargs.get("initial", {})
            initial.setdefault("username", username)
            kwargs["initial"] = initial

        super(KSAuthForm, self).__init__(request, *args, **kwargs)
        self.fields["username"].widget.attrs["readonly"] = True

    def clean_username(self):
        instance = getattr(self, "instance", None)
        if instance:
            if instance.is_disabled:
                return instance.username
            else:
                return self.cleaned_data.get("username")
