
from django.shortcuts import render
from django.views import generic

from status.models import System
from news.models import Outage

def index(request):
    systems = System.objects.order_by("-name")
    for system in systems:
        # put something real here
        system.status = "unknown"
        system.load = "unknown"
        print("new info: %s %s" % (system.status,system.load))
    
    outages = Outage.objects.order_by("-start_date")
    outages = filter(lambda outage: outage.status == "P" or outage.status == "O",outages)

    context = {"systems": systems,
               "outages": outages}

    return render(request, 'status/index.html', context)

# not used right now
class IndexView(generic.ListView):
    template_name = "status/index.html"
    context_object_name = "system_list"

    def get_queryset(self):
        """Return the known systems."""
        systems = System.objects.order_by("-name")
        for system in systems:
            # put something real here
            system.status = "unknown"
            system.load = "unknown"
            print("new info: %s %s" % (system.status,system.load))
        return systems


class DetailView(generic.DetailView):
    model = System
    template_name = "status/detail.html"

