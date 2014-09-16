
from django.db import models
from django.contrib.auth.models import User

from status.models import System

class News(models.Model):
    title = models.CharField(max_length=100)
    publish_date = models.DateTimeField('date published')
    author = models.ForeignKey(User)
    image = models.CharField(max_length=200,blank=True)
    short_description = models.TextField(max_length=100,default="")
    long_description = models.TextField(max_length=2000,default="")

    def __unicode__(self):
        return self.title

    class Meta:
        abstract = True

class Announcement(News):
    pass

class Event(News):
    TYPE = (
        ("Co","Conference"),
        ("Wo","Workshop"),
        ("Pa","Paper"),
        ("Po","Poster"),
        ("Pr","Presentation"),
        ("Tu","Tutorial"),
    )
    typ = models.CharField(max_length=2,choices=TYPE,verbose_name="type")

class Outage(News):
    STATUS = (
        ("P","Planned"),
        ("O","Ongoing"),
        ("R","Resolved"),
    )
    REASON = (
        ("M","Maintenance"),
        ("S","Software System Failure"),
        ("H","Hardware Failure"),
        ("N","Network Failure"),
        ("O","Other Failure"),
    )
    current_status = models.CharField(max_length=1,choices=STATUS)
    reason = models.CharField(max_length=1,choices=REASON)
    affected_systems = models.ManyToManyField(System)
    #affected_services ?
    start_date = models.DateTimeField('start of outage')
    end_date = models.DateTimeField('expected end of outage')
    resolution = models.TextField(max_length=2000)


