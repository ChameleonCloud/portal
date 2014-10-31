from django.contrib import admin
from news.models import Announcement,Event,Outage

# Register your models here.

admin.site.register(Announcement)
admin.site.register(Event)
admin.site.register(Outage)
