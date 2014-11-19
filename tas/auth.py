from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from pytas.pytas import client as TASClient
import logging
import re

class TASBackend(object):

    def __init__(self):
        self.tas = TASClient()

    # Create an authentication method
    # This is called by the standard Django login procedure
    def authenticate(self, username=None, password=None,errors=[]):
        tas_user = None
        try:
            # Check if this user is valid on the mail server
            if self.tas.authenticate(username, password):
                tas_user = self.tas.get_user(username=username)
            else:
                raise Exception('Authentication Error', 'Your username or password is incorrect.')
        except Exception as e:
            logger = logging.getLogger('auth')
            logger.error(e.args)
            if re.search(r'PendingEmailConfirmation', e.args[1]):
                raise ValidationError('Please confirm your email address before logging in.')
            else:
                raise ValidationError(e.args[1])

        UserModel = get_user_model()
        try:
            # Check if the user exists in Django's local database
            user = UserModel.objects.get(username=username)
            user.first_name = tas_user['firstName']
            user.last_name = tas_user['lastName']
            user.email = tas_user['email']
            user.save()

        except UserModel.DoesNotExist:
            # Create a user in Django's local database
            user = UserModel.objects.create_user(
                username=username,
                first_name=tas_user['firstName'],
                last_name=tas_user['lastName'],
                email=tas_user['email']
                )

        return user

    # Required for your backend to work properly - unchanged in most scenarios
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
