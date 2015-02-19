from django.http import HttpResponse
from django.views.generic import TemplateView
from django.conf import settings
from .g5k_discovery_api import G5K_API
import json

api = G5K_API()

class DiscoveryView(TemplateView):
    template_name = 'g5k_discovery/item.html'

    def get_context_data(self, **kwargs):
        context = super(DiscoveryView, self).get_context_data(**kwargs)
        resource = '/'
        if 'resource' in kwargs:
            resource = kwargs['resource']

        data = api.call(resource)

        if 'items' in data:
            parent_link = [link for link in data['items'][0]['links'] if link['rel'] == 'parent']
            parent_item = api.call(parent_link[0]['href'])
            context['items'] = data['items']
            context['parent_item'] = parent_item
            self.template_name = 'g5k_discovery/collection.html'
        else:
            context['item'] = data

        return context

def g5k_json(request, resource):
    data = api.call(resource)
    return HttpResponse(json.dumps(data), content_type='application/json')
