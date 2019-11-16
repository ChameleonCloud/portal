import re
import requests

from .conf import ZENODO_SANDBOX

import logging
LOG = logging.getLogger(__name__)

class ZenodoClient:
  @staticmethod
  def to_record(doi):
    if not doi:
        raise Exception('No DOI provided')
    elif not re.match(r'10\.[0-9]+\/zenodo\.[0-9]+$', doi):
        raise Exception('DOI is invalid (wrong format)')
    else:
        return doi.split('.')[-1]
        
  
  def __init__(self):
    self.base_url = 'https://sandbox.zenodo.org/api/' if ZENODO_SANDBOX else 'https://zenodo.org/api/'


  def _make_request(self, path, **kwargs):
    res = requests.request(
      method=kwargs.get('method', 'GET'),
      url='{}/{}'.format(self.base_url, path),
      headers={'accept': 'application/json'},
      **kwargs
    )
    res.raise_for_status()
    return res.json()


  def get_versions(self, doi):
    record = self._make_request('records/{}'.format(ZenodoClient.to_record(doi)))
    search_result = self._make_request('records', params={
      'q': 'conceptdoi:"{}"'.format(record['conceptdoi']),
      'all_versions': True
    })

    versions = None
    # Zenodo seems to return a list of results when requesting via
    # 'requests' library, yet returns a wrapped standard Elasticsearch
    # response otherwise (e.g., with cURL). Assume either could happen.
    if isinstance(search_result, list):
      versions = search_result
    elif 'hits' in search_result:
      versions = search_result.get('hits', {}).get('hits', [])
    
    if not versions:
      raise ValueError('Got invalid response when fetching all versions for {}'.format(doi))

    return versions
