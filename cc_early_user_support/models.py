from django.conf import settings
from django.db import models

class EarlyUserPeriod(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __unicode__(self):
        return self.name


REQUESTED = 'REQ'
APPROVED = 'APP'
DENIED = 'DEN'
EARLY_USER_REQUEST_STATUS_CHOICES = (
    (REQUESTED, 'Requested'),
    (APPROVED, 'Approved'),
    (DENIED, 'Denied'),
)


class EarlyUserRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, )
    justification = models.TextField()
    request_status = models.CharField(
        max_length=3,
        choices=EARLY_USER_REQUEST_STATUS_CHOICES,
        default=REQUESTED
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.user.username

    class Meta:
        verbose_name = 'Early User Request'
        verbose_name_plural = 'Early User Requests'
