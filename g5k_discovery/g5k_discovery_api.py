import requests
import json
from django.conf import settings

class G5K_API:

    def call( self, endpoint ):
        resp = requests.get( self.make_url( endpoint ) )
        data = resp.json()
        return data

    def make_url( self, endpoint ):    	
        return '{0}/{1}.{2}'.format( settings.G5K_API_ROOT, endpoint, 'json')
