from django.http import HttpResponse
from django.views.generic import TemplateView
from django.shortcuts import render_to_response
from django.conf import settings
from .g5k_discovery_api import G5K_API
import json

api = G5K_API()

class DiscoveryView(TemplateView):
    template_name = 'g5k_discovery/discovery.html'

    def get_context_data(self, **kwargs):
        context = super(DiscoveryView, self).get_context_data(**kwargs)
        return context

def g5k_json(request, resource):
    data = api.call(resource)
    return HttpResponse(json.dumps(data), content_type='application/json')

def g5k_html(request, resource):
    templateUrl = 'g5k_discovery/%s.html' %resource
    return render_to_response(templateUrl)
