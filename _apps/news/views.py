from django.shortcuts import render
from django.views import generic

from news.models import Announcement,Event,Outage

NUMBER_RECENT = 4

def index(request):
    announcements = Announcement.objects.order_by("-publish_date")
    events = Event.objects.order_by("-publish_date")
    outages = Outage.objects.order_by("-start_date")

    context = {"announcements": announcements,
               "events": events,
               "outages": outages}

    return render(request, 'news/index.html', context)

def announcements(request):
    announcements = Announcement.objects.order_by("-publish_date")

    context = {"recent_announcements": announcements[:NUMBER_RECENT],
               "older_announcements": announcements[NUMBER_RECENT:]}

    return render(request, 'news/announcements.html', context)

class AnnouncementView(generic.DetailView):
    model = Announcement
    template_name = "news/announcement.html"

def events(request):
    events = Event.objects.order_by("-publish_date")

    context = {"recent_events": events[:NUMBER_RECENT],
               "older_events": events[NUMBER_RECENT:]}

    return render(request, 'news/events.html', context)

class EventView(generic.DetailView):
    model = Event
    template_name = "news/event.html"

class OutageView(generic.DetailView):
    model = Outage
    template_name = "news/outage.html"

def outages(request):
    outages = Outage.objects.order_by("-start_date")

    context = {"recent_outages": outages[:NUMBER_RECENT],
               "older_outages": outages[NUMBER_RECENT:]}

    return render(request, 'news/outages.html', context)
