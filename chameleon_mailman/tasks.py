from __future__ import absolute_import, unicode_literals

from celery import shared_task

from django.core.mail import send_mail


@shared_task
def schedule_email(*args, **kwargs):
    send_mail(*args, **kwargs)
