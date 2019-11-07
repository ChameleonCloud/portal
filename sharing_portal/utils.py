import json
import re

from django.conf import settings
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from .conf import ZENODO_SANDBOX


def get_rec_id(doi):
    """Parses Zenodo DOI to isolate record id

    Parameters
    ----------
    doi : string
        doi to isolate record id from; must not be empty

    Returns
    ------
    string
        The Zenodo record id at the end of the doi

    Notes
    -----
    - DOIs are expected to be in the form 10.xxxx/zenodo.xxxxx
    - Behaviour is undefined if they are given in another format
    """

    if not doi:
        raise Exception("No doi")
    elif not re.match(r'10\.[0-9]+\/zenodo\.[0-9]+$', doi):
        raise Exception("Doi is invalid (wrong format)")
    else:
        record_id = doi.split('.')[-1]
        return record_id


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
    req = Request(
        "{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )
    resp = urlopen(req)
    record = json.loads(resp.read().decode("utf-8"))

    # If there's a newer version, use that
    latest = record.get('links', {}).get('latest')
    if (latest):
        req = Request(
            "{}".format(latest),
            headers={"accept": "application/json"},
        )
        resp = urlopen(req)
        record = json.loads(resp.read().decode("utf-8"))
        record_id = get_rec_id(record['doi'])

    # Return the assembled string
    return "record/" + record_id + "/files/" + record['files'][0]['filename']
