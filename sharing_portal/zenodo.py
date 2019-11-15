import re
import requests

from .conf import ZENODO_SANDBOX

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
    return res.json()


  def get_versions(self, doi):
    record = self._make_request('records/{}'.format(ZenodoClient.to_record(doi)))
    search_result = self._make_request('records', params={
      'q': 'conceptdoi:"{}"'.format(record['conceptdoi']),
      'all_versions': True
    })
    return search_result.get('hits', {}).get('hits', [])
