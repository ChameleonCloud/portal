import re

from ckeditor.fields import RichTextField
from cms.models.pluginmodel import CMSPlugin
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.template.defaultfilters import slugify


class NewsTag(models.Model):
    tag = models.TextField(max_length=50)

    def __str__(self):
        return self.tag

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"


"""
Super class for all news content
"""


class News(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    summary = RichTextField(max_length=600)
    body = RichTextField()
    tags = models.ManyToManyField(NewsTag, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "News"
        verbose_name_plural = "News"

    def save(self):
        if not self.slug:
            self.slug = slugify(self.title)
        super(News, self).save()


"""
Implementation for Events
"""


class Event(News):
    EVENT_TYPES = (
        ("WEBINAR", "Webinar"),
        ("CONFERENCE", "Conference"),
        ("MEETING", "Meeting"),
        ("PAPER", "Paper"),
        ("POSTER", "Poster"),
        ("PRESENTATION", "Presentation"),
        ("TUTORIAL", "Tutorial"),
        ("WORKSHOP", "Workshop"),
        ("OTHER", "Other"),
    )
    event_type = models.TextField(choices=EVENT_TYPES)
    registration_link = models.CharField(max_length=500, blank=False, default="")
    event_date = models.DateTimeField("event date")

    def save(self):
        if not self.slug:
            self.slug = "%s-%s" % (
                self.event_date.strftime("%y-%m-%d"),
                slugify(self.title),
            )
        super(Event, self).save()


"""
Implementation for System Outages
"""


class Outage(News):
    start_date = models.DateTimeField("start of outage")
    end_date = models.DateTimeField("expected end of outage")
    resolved = models.BooleanField("resolved", default=False)
    send_email_notification = False
    reminder_sent = models.DateTimeField("reminder_sent", null=True, blank=True)

    SEVERITY_LEVEL = (
        ("", ""),
        ("SEV-1", "SEV-1"),
        ("SEV-2", "SEV-2"),
        ("SEV-3", "SEV-3"),
    )
    severity = models.CharField(
        choices=SEVERITY_LEVEL, blank=False, default="", max_length=50
    )

    def save(self):
        if not self.slug:
            self.slug = "%s-%s" % (
                self.start_date.strftime("%y-%m-%d"),
                slugify(self.title),
            )
        super(Outage, self).save()


class OutageUpdate(News):
    original_item = models.ForeignKey(Outage, on_delete=models.CASCADE)


"""
This class represents a notification which should be displayed to users using
the django.contrib.messages framework. Messages can be created and scheduled
for display.
"""


class Notification(models.Model):
    NOTIFICATION_LEVELS = (
        (messages.INFO, "Informational"),
        (messages.SUCCESS, "Success"),
        (messages.WARNING, "Warning"),
        (messages.ERROR, "Error"),
    )

    level = models.IntegerField(choices=NOTIFICATION_LEVELS)
    title = models.CharField(max_length=80, blank=True)
    message = models.TextField()
    schedule_on = models.DateTimeField("scheduled display start", blank=True)
    schedule_off = models.DateTimeField("scheduled display end", blank=True)
    limit_pages = models.TextField(
        "Limit display only to these page paths (one per line)", blank=True
    )

    def __str__(self):
        if self.title:
            return self.title
        else:
            return self.message

    def display(self):
        return re.sub(r"\s+", " ", "<h4>{0}</h4>{1}".format(self.title, self.message))


"""
User News CMS Plugin Model
"""


class UserNewsPluginModel(CMSPlugin):
    limit = models.IntegerField(default=5)
    display_news = models.BooleanField(default=True)
    display_events = models.BooleanField(default=True)
    display_outages = models.BooleanField(default=True)
