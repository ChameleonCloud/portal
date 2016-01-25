from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

@apphook_pool.register
class RTApphook(CMSApp):
    name = _('RT Apphook')
    urls = ['djangoRT.urls']
    app_name = 'djangoRT'

@apphook_pool.register
class ProjectsApphook(CMSApp):
    name = _('Projects Apphook')
    urls = ['projects.urls']
    app_name = 'projects'

@apphook_pool.register
class TASApphook(CMSApp):
    name = _('TAS Apphook')
    urls = ['tas.urls']
    app_name = 'tas'

@apphook_pool.register
class ResourceDiscoveryApphook(CMSApp):
    name = _('Resource Discovery Apphook')
    urls = ['g5k_discovery.urls']
    app_name = 'g5k_discovery'

@apphook_pool.register
class ApplianceCatalogApphook(CMSApp):
    name = _('Appliance Catalog Apphook')
    urls = ['appliance_catalog.urls']
    app_name = 'appliance_catalog'