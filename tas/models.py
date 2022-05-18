from django.db import models
from django.contrib.auth import get_user_model


def activate_local_user(username):
    try:
        UserModel = get_user_model()
        local_user = UserModel.objects.get(username=username)
        local_user.is_active = True
        local_user.save()
    except:
        pass


def user_is_active(username):
    try:
        UserModel = get_user_model()
        local_user = UserModel.objects.get(username=username)
        return local_user.is_active
    except:
        pass
