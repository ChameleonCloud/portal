from csp.decorators import csp_update
from django.http import HttpResponse
from django.shortcuts import render_to_response, render
from django.conf import settings
from .g5k_discovery_api import G5K_API
import json
import logging

logger = logging.getLogger("default")

api = G5K_API()


# NOTE(jason): we need to add 'unsafe-eval' here (;-;) because the jspath
# library used by this page apparently relies on creating new Function()s in
# JS to do its filtering.
@csp_update(SCRIPT_SRC="'unsafe-eval'")
def index(request):
    return render(request, "g5k_discovery/discovery.html")


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
