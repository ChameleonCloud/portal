from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.html import strip_tags

import logging

logger = logging.getLogger(__name__)

class MailmanSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='subscriptions')
    outage_notifications = models.BooleanField(
            default=True,
            help_text=_('Notifications about maintenance downtimes and outages'))
    users_list = models.BooleanField(
            default=True,
            help_text=_('Mailing list for discussion among Chameleon Users'))

@receiver(post_save, sender='user_news.Outage')
def send_outage_notification(sender, instance, using, **kwargs):
    """
    Sends email notification to the address configured in `settings.OUTAGE_NOTIFICATION_EMAIL`.
    Will send "new" notifications when the object is new.
    """
    if instance.send_email_notification:
        logger.debug('Sending outage notification for id=%s: %s' % (instance.id, instance.title))

        subject = instance.title
        if instance.resolved:
            subject = 'RESOLVED: %s' % subject

        body = instance.body
        sender = settings.DEFAULT_FROM_EMAIL
        recipients = settings.OUTAGE_NOTIFICATION_EMAIL.split(',')

        send_mail(subject, strip_tags(body), sender, recipients, html_message=body)