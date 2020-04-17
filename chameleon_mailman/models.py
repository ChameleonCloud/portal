from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.html import strip_tags

from chameleon.celery import app
from .tasks import schedule_email

from datetime import timedelta
from itertools import chain
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
    subject = instance.title
    if instance.resolved:
        subject = 'RESOLVED: %s' % subject

    body = "<b>Outage Start:</b> " + instance.start_date.strftime('%Y-%m-%d %H:%M') + "<br /><br />"
    body += "<b>Outage End:</b> " + instance.end_date.strftime('%Y-%m-%d %H:%M') + "<br /><br />"
    body += instance.body
    sender = settings.DEFAULT_FROM_EMAIL
    recipients = settings.OUTAGE_NOTIFICATION_EMAIL.split(',')

    if instance.send_email_notification:
        logger.debug('Sending outage notification for id=%s: %s' % (instance.id, instance.title))

        send_mail(subject, strip_tags(body), sender, recipients, html_message=body)

    if instance.send_email_reminder:

        celery_queue = app.control.inspect()
        scheduled_tasks = list(chain(*celery_queue.scheduled().values()))
        existing_tasks = [
            int(x['request']['id'].split('-')[-1]) for x in scheduled_tasks
            if str(instance.id) in x['request']['id']]

        task_id = "{}-0".format(str(instance.id))

        if existing_tasks:
            last_task_id = "{}-{}".format(
                str(instance.id), str(max(existing_tasks)))
            app.control.revoke(last_task_id)

            task_id = "{}-{}".format(
                str(instance.id), str(max(existing_tasks) + 1))

        eta = instance.start_date - timedelta(
            seconds=settings.OUTAGE_EMAIL_REMINDER_TIMEDELTA)
        subject = 'Outage Reminder: {}'.format(subject)

        schedule_email.apply_async(
            (subject, strip_tags(body), sender, recipients),
            kwargs=dict(html_message=body), eta=eta, task_id=task_id)
