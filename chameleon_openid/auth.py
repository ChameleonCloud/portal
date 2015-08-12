from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

import logging

logger = logging.getLogger(__name__)

class OpenIDBackend(ModelBackend):

    # Create an authentication method
    # This is called by the standard Django login procedure
    def authenticate(self, openid_identity=None, **kwargs):
        user = None
        if openid_identity is not None:
            pass

        return user
