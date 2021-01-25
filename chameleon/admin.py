"""Module to manage PI Eligibility Requests."""

import logging
import re
import urllib.parse
from functools import wraps

from chameleon.models import PIEligibility
from django.contrib import admin
from django.contrib.admin.utils import flatten
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
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


class PIEligibilityAdmin(admin.ModelAdmin):
    """Class to define valid fields and methods for PI Eligibility DB entries."""

    readonly_fields = [
        "requestor",
        "request_date",
        "user_metadata",
        "reviewer",
        "review_date",
    ]
    fields = (
        "requestor",
        "request_date",
        "user_metadata",
        "status",
        "review_date",
        "reviewer",
        "review_summary",
    )
    ordering = ["-status", "-request_date", "-review_date"]

    list_display = ("requestor", "status", "request_date")
    list_filter = ("status",)
    search_fields = ["requestor__username"]

    def keycloak_metadata(self, obj):
        """User metadata from keycloak backend."""
        keycloak_client = KeycloakClient()
        keycloak_user = keycloak_client.get_user_by_username(obj.requestor.username)

        if not keycloak_user:
            return "No Keycloak User Found"

        full_name = "{} {}".format(
            keycloak_user["lastName"], keycloak_user["firstName"]
        )
        email = keycloak_user["email"]
        contents = [f"Name: {full_name}", f"Email: {email}"]

        if not contents:
            return "No Keycloak Metadata Found"

        for key, val in keycloak_user["attributes"].items():
            if key not in ["joinDate"]:
                # convert camelcase to separate out words
                key = re.sub("([A-Z])", " \\1", key).strip().capitalize()
                contents.append(f"{key}: {val}")

        return "\n".join(contents)

    def orcid_metadata(self, obj):
        """
        Get metadata for orcid users.

        This is the fast and dirty way, by checking substrings against the ORCiD
        ID format. The actual ORCiD ID has the last digit as a checksum, and
        strongly recommends using an OAUTH flow to get authenticated results.

        The regex below CANNOT validate that an orcid ID exists, or points to the
        correct user.
        """
        orcid_id_regex = r"\d{4}-\d{4}-\d{4}-(?:\d{3}[xX]|\d{4})"

        def get_orcid_ids(input_str, regex):
            """Return all substrings matching regex."""
            match = re.findall(regex, input_str)
            logger.debug(f"ORCiD Match on {input_str} results in: {match}")
            return match

        def get_orcid_url(orcid_id):
            """Return url of form https://orcid.org/0000-0012-2345-6789."""
            base_url = "https://orcid.org/"
            result = urllib.parse.urljoin(base_url, orcid_id)
            logger.debug(f"converting {orcid_id} to {result}")
            return result

        # Get all matching substrings, regex can output array
        checked_ids = flatten(
            [
                get_orcid_ids(ident, orcid_id_regex)
                for ident in [obj.requestor.username, obj.requestor.email]
            ]
        )

        if not checked_ids:
            return "No ORCiD User Found"

        orcid_urls = [get_orcid_url(orcid_id) for orcid_id in checked_ids]

        if not orcid_urls:
            return f"Bad URL for ids: {checked_ids} "
        else:
            return "\n".join(orcid_urls)

    def user_metadata(self, obj):
        """Populate user metadata with discovered info from federation."""
        logger.debug(f"Fetching metadata for user {obj.requestor}")
        metadata_arr = []
        try:
            metadata_arr.append(self.keycloak_metadata(obj))
            metadata_arr.append(self.orcid_metadata(obj))
        except Exception as err:
            logger.debug(f"Failed to add metadata, error: {err}")

        return "\n".join(metadata_arr)


admin.site.register(PIEligibility, PIEligibilityAdmin)
