from django.contrib.auth import get_user_model
from pytas.pytas import client as TASClient

class TASBackend(object):

    def __init__(self):
        self.tas = TASClient()

    # Create an authentication method
    # This is called by the standard Django login procedure
    def authenticate(self, username=None, password=None):
        UserModel = get_user_model()
        try:
            # Check if this user is valid on the mail server
            if not self.tas.authenticate(username, password):
                raise Exception('The username or password is incorrect.')
        except:
            return None

        try:
            # Check if the user exists in Django's local database
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Create a user in Django's local database
            user = UserModel.objects.create_user(username)
        return user

    # Required for your backend to work properly - unchanged in most scenarios
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
