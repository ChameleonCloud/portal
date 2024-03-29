import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger("default")


class EDGE_HW_API:
    def get_devices(self):
        url = self.make_url("devices")
        logger.info("Requesting %s from Edge HW API ...", url)
        resp = requests.get(url)
        logger.info("Response received. Parsing to json ...")
        return resp.json()

    def make_url(self, endpoint):
        return "{0}/{1}".format(settings.EDGE_HW_ROOT, endpoint)
