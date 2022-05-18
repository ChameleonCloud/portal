import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger("default")


class G5K_API:
    def call(self, endpoint):
        url = self.make_url(endpoint)
        logger.info("Requesting %s from reference API ...", url)
        resp = requests.get(url)
        logger.info("Response received. Parsing to json ...")
        data = resp.json()
        return data

    def make_url(self, endpoint):
        return "{0}/{1}.{2}".format(settings.G5K_API_ROOT, endpoint, "json")
