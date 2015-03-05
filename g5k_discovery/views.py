from django.http import HttpResponse
from django.views.generic import TemplateView
from django.conf import settings
from .g5k_discovery_api import G5K_API
import json

api = G5K_API()

class DiscoveryView(TemplateView):
    template_name = 'g5k_discovery/discovery.html'

    def get_context_data(self, **kwargs):
        context = super(DiscoveryView, self).get_context_data(**kwargs)
    #     #resource = '/'
    #     #if 'resource' in kwargs:
    #     #    resource = kwargs['resource']
    #     allnodes = []
    #     selectednodes = []
    #     data = api.call('sites')
    #     for item in data['items']:
    #         clusters_link = [link for link in item['links'] if link['rel'] == 'clusters']
    #         clusters = api.call(clusters_link[0]['href'])
    #         for cluster in clusters['items']:
    #             nodes_link = [link for link in cluster['links'] if link['rel'] == 'nodes']
    #             nodes = api.call(nodes_link[0]['href'])
    #             for node in nodes['items']:
    #                 allnodes.append(node)
    #
    #     context['allnodes'] = allnodes
        return context

def g5k_json(request, resource):
    data = api.call(resource)
    return HttpResponse(json.dumps(data), content_type='application/json')
