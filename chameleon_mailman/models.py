from django.conf import settings
from django.db import models


class MailmanSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    outage_notifications = models.BooleanField(default=True)
