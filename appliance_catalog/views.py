from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from .models import Appliance
import logging

logger = logging.getLogger("default")


def app_detail(request, pk):
    logger.info("Detail requested for appliance id: %s.", pk)
    appliance = get_object_or_404(Appliance, pk=pk)
    if appliance.redirect_url:
        return HttpResponseRedirect(appliance.redirect_url)
    raise Http404
