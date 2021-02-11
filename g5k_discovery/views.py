import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, render_to_response
from django.views.generic import TemplateView

from .g5k_discovery_api import G5K_API

logger = logging.getLogger("default")

api = G5K_API()


class DiscoveryView(TemplateView):
    template_name = "g5k_discovery/discovery.html"

    def get_context_data(self, **kwargs):
        context = super(DiscoveryView, self).get_context_data(**kwargs)
        return context


def g5k_json(request, resource):
    logger.info("Resource requested: %s.json, by user: %s", resource, request.user)
    data = api.call(resource)
    logger.debug("Response excerpt: %s ...", json.dumps(data)[0:200])
    return HttpResponse(json.dumps(data), content_type="application/json")


def g5k_html(request, resource):
    logger.info("Template requested: %s.html", resource)
    templateUrl = "g5k_discovery/%s.html" % resource
    return render_to_response(templateUrl)


# basically writing two more identical functions because angular is a fucking piece of shit :)
# TODO figure out how to do this right?
def node_view(request, resource):
    data = api.call(resource)
    site = resource.split("/")[1]
    cluster = resource.split("/")[3]
    return render(
        request,
        "g5k_discovery/node_details.html",
        {"node": data, "resource": resource, "site": site, "cluster": cluster},
    )


def node_data(request, resource):
    data = api.call(resource)
    return HttpResponse(json.dumps(data), content_type="application/json")
