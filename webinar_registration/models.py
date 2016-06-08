from django.conf import settings
from django.db import models
#from datetime import datetime
from django.utils import timezone
import pytz

class Webinar(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    registration_open = models.DateTimeField()
    registration_closed = models.DateTimeField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    registration_limit = models.IntegerField(default=0)

    def is_registration_open(self):
        utc=pytz.UTC
        return self.registration_open <= timezone.now()

    def is_registration_closed(self):
        utc = pytz.UTC
        return self.registration_closed >= timezone.now()

    def is_registration_future(self):
        utc = pytz.UTC
        return self.registration_open > timezone.now()

    def __unicode__(self):
        return self.name

    def is_registered(self, is_registered):
        self.is_registered = is_registered

    class Meta:
        verbose_name = 'Webinar'
        verbose_name_plural = 'Webinars'


class WebinarRegistrant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, )
    webinar = models.ForeignKey(Webinar, )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.user.username

    class Meta:
        verbose_name = 'Webinar Registrant'
        verbose_name_plural = 'Webinar Registrants'
