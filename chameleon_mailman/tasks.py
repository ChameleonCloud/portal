

from datetime import datetime, timedelta
import logging
import pytz

from celery.decorators import task

from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from user_news.models import Outage

logger = logging.getLogger(__name__)


@task
def send_outage_reminders(crontab_frequency, send_outage_reminder_before):
    now = datetime.now(pytz.utc)
    upcoming_outages = Outage.objects.filter(start_date__gte=now)
    upcoming_outages = upcoming_outages.filter(reminder_sent__isnull=True)

    send_window_max = now + timedelta(seconds=send_outage_reminder_before)
    send_window_min = send_window_max - timedelta(
        seconds=(crontab_frequency * 60))

    for outage in upcoming_outages.all():
        # Check for an outage scheduled close to start date
        if outage.start_date < outage.created + timedelta(days=1):
            outage.reminder_sent = outage.created
            outage.save()
            continue

        if send_window_min < outage.start_date < send_window_max:

            subject = "Outage Reminder: {}".format(outage.title)
            body = "<b>Outage Start:</b> {}<br /><br />".format(
                outage.start_date.strftime("%Y-%m-%d %H:%M")
            )
            body += "<b>Outage End:</b> {}<br /><br />".format(
                outage.end_date.strftime("%Y-%m-%d %H:%M")
            )
            body += outage.body
            sender = settings.DEFAULT_FROM_EMAIL
            recipients = settings.OUTAGE_NOTIFICATION_EMAIL.split(",")

            mail_sent = send_mail(
                subject, strip_tags(body), sender, recipients, html_message=body
            )

            if mail_sent:
                outage.reminder_sent = now
                outage.save()
