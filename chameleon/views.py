
from django.shortcuts import render
from django.views import generic

from news.models import Announcement

site = {
    "title": "Chameleon Cloud",
    "email": "contact@chameleoncloud.org",
    "description" : "Chameleon is a large-scale, reconfigurable experimental environment for next generation cloud research.",
    "baseurl": "/dev",
    "url": "http://www.chameleoncloud.org"
}

def home(request):
    announcements = Announcement.objects.order_by("-publish_date")
    my_data = {"announcements": announcements[:2]}

    context = dict(site.items() + my_data.items())

    return render(request, 'index.html', context)
