from django.db import models
from django.conf import settings

class UserProperties(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)
    is_pi_eligible = models.BooleanField(default=False)
