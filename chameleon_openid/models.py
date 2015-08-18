from django.db import models
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

@python_2_unicode_compatible
class OpenIDStore(models.Model):
    server_url = models.CharField(max_length=255)
    handle = models.CharField(max_length=255)
    secret = models.TextField()
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField()

    def __str__(self):
        return self.server_url


@python_2_unicode_compatible
class OpenIDNonce(models.Model):
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.server_url


@python_2_unicode_compatible
class OpenIDUserIdentity(models.Model):
    uid = models.CharField(unique=True, verbose_name=_('uid'), max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="openid_identities")
    last_login = models.DateTimeField(verbose_name=_('last login'), auto_now=True)
    date_joined = models.DateTimeField(verbose_name=_('date joined'), auto_now_add=True)

    def __str__(self):
        return self.uid

