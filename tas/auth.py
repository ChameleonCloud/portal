from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from pytas.http import TASClient
from chameleon.keystone_auth import disable_user
import logging
import re


class TASBackend(ModelBackend):
    def __init__(self):
        self.tas = TASClient()

    # Create an authentication method
    # This is called by the standard Django login procedure
    def authenticate(self, username=None, password=None, request=None, **kwargs):
        if username is None or password is None:
            return None

        logger = logging.getLogger("tas")
        if request is not None:
            logger.info(
                'Attempting login for user "%s" from IP "%s"'
                % (username, request.META.get("REMOTE_ADDR"))
            )
        else:
            logger.info(
                'Attempting login for user "%s" from IP "%s"' % (username, "unknown")
            )

        tas_user = None
        try:
            if self.tas.authenticate(username, password):
                tas_user = self.tas.get_user(username=username)
                logger.info('Login successful for user "%s"' % username)
            else:
                raise ValidationError(
                    "Authentication Error", "Your username or password is incorrect."
                )
        except Exception as e:
            logger.error(e.args)
            if re.search(r"PendingEmailConfirmation", e.args[1]):
                raise ValidationError(
                    "Please confirm your email address before logging in."
                )
            else:
                raise ValidationError(e.args[1])

        if tas_user is not None:
            UserModel = get_user_model()
            try:
                # Check if the user exists in Django's local database
                user = UserModel.objects.get(username=username)
                if not user.is_active:
                    # Also ensure the user can no longer access any site
                    disable_user(username)
                    raise ValidationError(
                        "Your account is inactive, for assistance please open a Helpdesk ticket."
                    )

                user.first_name = tas_user["firstName"]
                user.last_name = tas_user["lastName"]
                user.email = tas_user["email"]
                user.save()

            except UserModel.DoesNotExist:
                # Create a user in Django's local database
                user = UserModel.objects.create_user(
                    username=username,
                    first_name=tas_user["firstName"],
                    last_name=tas_user["lastName"],
                    email=tas_user["email"],
                )

        return user
