from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect
from django.utils.html import strip_tags

from tas.forms import UserProfileForm
from util.project_allocation_mapper import ProjectAllocationMapper
from util.keycloak_client import DuplicateUserError

import logging

LOG = logging.getLogger(__name__)


@login_required
def profile(request):
    context = {}
    mapper = ProjectAllocationMapper(request)
    context["profile"] = mapper.get_user(request.user)
    context["piEligibility"] = context["profile"]["piEligibility"]

    return render(request, "tas/profile.html", context)


@login_required
def profile_edit(request):
    mapper = ProjectAllocationMapper(request)
    user_info = mapper.get_user(request.user)

    if request.method == "POST":
        request_pi_eligibility = request.POST.get("request_pi_eligibility")
        kwargs = {"is_pi_eligible": request_pi_eligibility}
        form = UserProfileForm(request.POST, initial=user_info, **kwargs)

        if form.is_valid():
            data = form.cleaned_data
            try:
                mapper.update_user_profile(request.user, data, request_pi_eligibility)
                messages.success(request, "Your profile has been updated!")
                return HttpResponseRedirect(reverse("tas:profile"))
            except DuplicateUserError:
                messages.error(request, "A user with this email already exists")
            except Exception:
                messages.error(request, "An error occurred updating your profile")
                LOG.exception(
                    (
                        "An unknown error occurred updating user profile for "
                        f"{request.user.username}"
                    )
                )
    else:
        kwargs = {"is_pi_eligible": False}
        if user_info["piEligibility"].upper() == "ELIGIBLE":
            kwargs = {"is_pi_eligible": True}
        form = UserProfileForm(initial=user_info, **kwargs)

    context = {
        "form": form,
        "user": user_info,
        "piEligibility": user_info["piEligibility"],
    }
    return render(request, "tas/profile_edit.html", context)


def send_opt_in_email(fname, email):
    try:
        template = "tas/email_subscription_opt_in.html"
        body = render_to_string(template, {"fname": fname})
        send_mail(
            subject="Welcome to Chameleon",
            message=strip_tags(body),
            from_email="no-reply@chameleoncloud.org",
            recipient_list=[email],
            fail_silently=False,
            html_message=body,
        )
    except Exception as e:
        LOG.error(e)
