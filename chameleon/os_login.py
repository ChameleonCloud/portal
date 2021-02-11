import logging

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login, logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from pytas.http import TASClient

from chameleon.keystone_auth import has_valid_token, regenerate_tokens
from util.project_allocation_mapper import ProjectAllocationMapper

LOG = logging.getLogger(__name__)


@csp_update(FRAME_ANCESTORS=settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request, current_app=None, extra_context=None):
    if request.GET.get(settings.FORCE_OLD_LOGIN_EXPERIENCE_PARAM) != "1":
        return HttpResponseRedirect(reverse("oidc_authentication_init"))

    login_return = login(request, current_app=None, extra_context=None)
    password = request.POST.get("password", False)
    if request.user.is_authenticated() and password:
        request.session["is_federated"] = False
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
    if (
        request.user.is_authenticated()
        and request.session.get("is_federated")
        and logout_redirect_url
    ):
        auth_logout(request)
        return HttpResponseRedirect(logout_redirect_url)

    return logout(request, next_page="/")


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
