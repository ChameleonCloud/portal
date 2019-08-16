import json
import re
from urllib.request import urlopen, Request

from .__init__ import DEV as dev

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


def get_zenodo_file(record_id):
    """ Get filename from deposition
    Parameters
    ----------
    record_id : string
        ID of deposition to get file from

    Returns
    -------
    string
        Retrieved file name

    Notes
    -----
    - No error handling
    """

    # Use Zenodo sandbox if in development
    if dev:
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
    print(record)

    # Return the first file's name
    return record['files'][0]['filename']
