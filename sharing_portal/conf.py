from django.conf import settings

JUPYTERHUB_URL = getattr(settings, 'SHARING_PORTAL_JUPYTERHUB_URL')

ZENODO_SANDBOX = getattr(settings, 'SHARING_PORTAL_ZENODO_SANDBOX', False)