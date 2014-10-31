from django.db import models
from tas.models import TASUser

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(TASUser)
