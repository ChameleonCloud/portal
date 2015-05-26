from django.conf import settings
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

class MailmanSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='subscriptions')
    outage_notifications = models.BooleanField(
            default=True,
            help_text=_('Notifications about maintenance downtimes and outages'))
    users_list = models.BooleanField(
            default=True,
            help_text=_('Mailing list for discussion among Chameleon Users'))
