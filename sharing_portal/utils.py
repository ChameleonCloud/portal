import json
import re
import requests

from django.conf import settings

from .conf import ZENODO_SANDBOX
from .zenodo import ZenodoClient


def get_zenodo_file_link(record_id):
    """ Get filename from deposition
    Parameters
    ----------
    record_id : string
        ID of deposition to get file from

    Returns
    -------
    string
        url suffix of the form 'record/<rec_id>/files/<filename>'

    Notes
    -----
    - No error handling
    """

    # Use Zenodo sandbox if in development
    if ZENODO_SANDBOX:
        api = "https://sandbox.zenodo.org/api/records/"
    else:
        api = "https://zenodo.org/api/records/"

    # Send a request to the Zenodo API
    res = requests.get("{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )
    record = res.json()

    # If there's a newer version, use that
    latest = record.get('links', {}).get('latest')
    if (latest):
        res = requests.get(
            "{}".format(latest),
            headers={"accept": "application/json"},
        )
        record = res.json()
        record_id = ZenodoClient.to_record(record['doi'])

    # Return the assembled string
    return "record/" + record_id + "/files/" + record['files'][0]['filename']
