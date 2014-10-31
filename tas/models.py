from django.db import models
from django.contrib.auth.models import AbstractBaseUser

# Create your models here.
class TASUser(AbstractBaseUser):
    username = models.CharField(max_length=8, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254)
    USERNAME_FIELD = 'username'
