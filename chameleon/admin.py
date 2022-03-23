"""Module to manage PI Eligibility Requests."""

import datetime
import re

from chameleon.models import PIEligibility
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils.html import (
    format_html_join,
    mark_safe,
    urlize,
    format_html,
    strip_tags,
)
from functools import wraps
import logging
import urllib.parse
from util.keycloak_client import KeycloakClient


logger = logging.getLogger(__name__)


def add_method(cls):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        setattr(cls, func.__name__, wrapper)
        return func

    return decorator


@add_method(get_user_model())
def pi_eligibility(self):
    try:
        return (
            PIEligibility.objects.filter(requestor=self).latest("request_date").status
        )
    except ObjectDoesNotExist:
        return "Ineligible"


class PIEligibilityAdmin(ModelAdmin):
    """Class to define valid fields and methods for PI Eligibility DB entries."""

    readonly_fields = [
        "requestor",
        "request_date",
        "user_metadata",
        "directory",
        "reviewer",
        "review_date",
    ]

    # Defines layout changes in add or change pages
    fields = (
        "requestor",
        "request_date",
        "user_metadata",
        "directory",
        "status",
        "review_date",
        "reviewer",
        "review_summary",
    )
    ordering = ["-status", "-request_date", "-review_date"]

    list_display = ("requestor", "status", "request_date")
    list_filter = ("status",)
    search_fields = ["requestor__username"]

    def _notify_user(self, pi_request, host):
        subject = f"Decision of your PI Eligibility request for {pi_request.requestor}"
        body = f"""
        <p>Your PI Eligibility status has been updated to {pi_request.status},
        due to the following reason:</p>
        <p>{pi_request.review_summary}</p>
        <br/>
        <p><i>This is an automatic email, please <b>DO NOT</b> reply!
        If you have any question or issue, please submit a ticket on our
        <a href="https://{host}/user/help/">help desk</a>.
        </i></p>
        <br/>
        <p>Thanks,</p>
        <p>Chameleon Team</p>
        """
        send_mail(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pi_request.requestor.email],
            message=strip_tags(body),
            html_message=body,
        )

    def save_model(self, request, obj, form, change):
        obj.reviewer = request.user
        obj.review_date = datetime.datetime.now()
        obj.save()
        self._notify_user(obj, request.get_host())

    def keycloak_metadata(self, obj):
        """User metadata from keycloak backend. Returns a list of strings."""
        keycloak_client = KeycloakClient()
        keycloak_user = keycloak_client.get_user_by_username(obj.requestor.username)

        if not keycloak_user:
            return "No Keycloak User Found"

        full_name = "{} {}".format(
            keycloak_user["lastName"], keycloak_user["firstName"]
        )
        email = keycloak_user["email"]
        yield [f"Name: {full_name}", f"Email: {email}"]

        for key, val in keycloak_user["attributes"].items():
            if key not in ["joinDate"]:
                # convert camelcase to separate out words
                key = re.sub("([A-Z])", " \\1", key).strip().capitalize()
                yield [(f"{key}: {val}")]

    def orcid_metadata(self, obj):
        """
        Get metadata for orcid users.

        This is the fast and dirty way, by checking substrings against the ORCiD
        ID format. The actual ORCiD ID has the last digit as a checksum, and
        strongly recommends using an OAUTH flow to get authenticated results.

        The regex below CANNOT validate that an orcid ID exists, or points to the
        correct user.
        """

        def get_orcid_ids(input_str):
            """Return all substrings matching regex."""
            orcid_id_regex = r"\d{4}-\d{4}-\d{4}-(?:\d{3}[xX]|\d{4})"
            match = re.findall(orcid_id_regex, input_str)
            logger.debug(f"ORCiD Match on {input_str} results in: {match}")
            return match

        def get_orcid_url(orcid_id):
            """Return url of form https://orcid.org/0000-0012-2345-6789."""
            base_url = "https://orcid.org/"
            result = urllib.parse.urljoin(base_url, orcid_id)
            logger.debug(f"converting {orcid_id} to {result}")
            return result

        for orcid_id in get_orcid_ids(obj.requestor.username):
            return get_orcid_url(orcid_id)

    def user_metadata(self, obj):
        """Populate user metadata with discovered info from federation."""
        logger.debug(f"Fetching metadata for user {obj.requestor}")
        try:
            keycloak_html = format_html_join(
                "", "{}<br>", (u for u in self.keycloak_metadata(obj))
            )
            orcid_html = urlize(self.orcid_metadata(obj))

        except Exception as err:
            logger.debug(f"Failed to add metadata, error: {err}")

        # return metadata_html
        return mark_safe(keycloak_html + orcid_html)

    def directory(self, obj):
        """Customize the department directory link."""
        return format_html(
            '<a href="{url}" target="_blank">{url}</a>'.format(
                url=obj.department_directory_link
            )
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["status"].widget.attrs.update(
            {"onchange": "getCannedResponsesPIEligibility(this.value)"}
        )
        return form

    class Media:
        js = ("scripts/cannedresponses.js",)


admin.site.register(PIEligibility, PIEligibilityAdmin)
