from django.contrib import admin

from user_news.forms import EventForm, OutageForm
from user_news.models import Event, News, NewsTag, Notification, Outage


class NewsAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


class EventAdmin(NewsAdmin):
    form = EventForm


class OutageAdmin(NewsAdmin):
    form = OutageForm


admin.site.register(NewsTag)
admin.site.register(News, NewsAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Outage, OutageAdmin)
admin.site.register(Notification)
