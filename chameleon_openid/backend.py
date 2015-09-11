from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from .models import OpenIDUserIdentity

import logging

logger = logging.getLogger(__name__)

class OpenIDBackend(ModelBackend):

    # Create an authentication method
    # This is called by the standard Django login procedure
    def authenticate(self, openid_identity=None, **kwargs):
        if openid_identity is not None:
            logger.info('Attempting to autheticate user for OpenID "%s"' % openid_identity)
            try:
                oid = OpenIDUserIdentity.objects.get(uid=openid_identity)
            except OpenIDUserIdentity.DoesNotExist:
                oid = None
            if oid:
                logger.info('User "%s" login using OpenID "%s"' % (oid.user, oid.uid))
                logger.info('Login successful for user "%s"' % oid.user)

                return oid.user

        return None
