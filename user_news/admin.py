from django.contrib import admin
from user_news.models import News, Event, Outage, NewsTag, Notification
from user_news.forms import EventForm, OutageForm

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
