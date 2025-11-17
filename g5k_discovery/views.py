from csp.decorators import csp_update
from django.http import HttpResponse
from django.shortcuts import render
from .g5k_discovery_api import G5K_API
import json
import logging
import requests

logger = logging.getLogger("default")

api = G5K_API()


def _get_chameleon_sites():
    sites_response = requests.get('https://api.chameleoncloud.org/sites', timeout=5)
    sites_response.raise_for_status()
    return sites_response


def _get_chameleon_sites_list():
    """Helper to fetch and return the list of Chameleon sites."""
    try:
        response = _get_chameleon_sites()
        return response.json().get('items', [])
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Failed to fetch chameleon sites for discovery page: {e}")
        return []


# NOTE(jason): we need to add 'unsafe-eval' here (;-;) because the jspath
# library used by this page apparently relies on creating new Function()s in
# JS to do its filtering.
@csp_update(SCRIPT_SRC="'unsafe-eval'")
def index(request):
    sites_list = _get_chameleon_sites_list()
    sites = {s['name'].replace('@', '_'): s for s in sites_list}
    return render(request, "g5k_discovery/discovery.html", {"sites": sites})


def g5k_json(request, resource):
    logger.info("Resource requested: %s.json, by user: %s", resource, request.user)
    data = api.call(resource)
    logger.debug("Response excerpt: %s ...", json.dumps(data)[0:200])
    return HttpResponse(json.dumps(data), content_type="application/json")


def g5k_html(request, resource):
    logger.info("Template requested: %s.html", resource)
    templateUrl = "g5k_discovery/%s.html" % resource
    return render(request, templateUrl)


# basically writing two more identical functions because angular is a fucking piece of shit :)
# TODO figure out how to do this right?
def node_view(request, resource):
    data = api.call(resource)
    site_uid = resource.split("/")[1]
    cluster = resource.split("/")[3]

    site_url = f'https://chi.{site_uid}.chameleoncloud.org'
    site_name = site_uid

    sites = _get_chameleon_sites_list()
    for site_info in sites:
        if site_info.get('uid') == site_uid:
            site_url = site_info.get('web', site_url)
            site_name = site_info.get('name', site_name)
            break

    return render(
        request,
        "g5k_discovery/node_details.html",
        {
            "node": data,
            "resource": resource,
            "site": site_name,
            "cluster": cluster,
            "site_url": site_url,
        },
    )


def node_data(request, resource):
    data = api.call(resource)
    return HttpResponse(json.dumps(data), content_type="application/json")


def chameleon_sites(request):
    try:
        sites_response = _get_chameleon_sites()
        return HttpResponse(sites_response.content, content_type='application/json')
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Failed to fetch chameleon sites: {e}")
        return HttpResponse(status=502, content='Error fetching data from Chameleon sites API')
