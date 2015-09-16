from django.http import HttpResponse
from django.views.generic import TemplateView
from django.shortcuts import render_to_response
from django.conf import settings
from .g5k_discovery_api import G5K_API
import json
import logging

logger = logging.getLogger('default')

api = G5K_API()

class DiscoveryView(TemplateView):
    template_name = 'g5k_discovery/discovery.html'

    def get_context_data(self, **kwargs):
        context = super(DiscoveryView, self).get_context_data(**kwargs)
        return context

def g5k_json(request, resource):
    logger.info('Resource requested: %s.json, by user: %s', resource, request.user)
    data = api.call(resource)
    logger.debug('Response excerpt: %s ...', json.dumps(data)[0:200]);
    return HttpResponse(json.dumps(data), content_type='application/json')

def g5k_html(request, resource):
    logger.info('Template requested: %s.html', resource)
    templateUrl = 'g5k_discovery/%s.html' %resource
    return render_to_response(templateUrl)