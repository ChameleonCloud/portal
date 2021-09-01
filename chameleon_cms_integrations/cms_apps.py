from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import gettext_lazy as _


@apphook_pool.register
class RTApphook(CMSApp):
    name = _('RT')
    app_name = 'djangoRT'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['djangoRT.urls']

@apphook_pool.register
class ProjectsApphook(CMSApp):
    name = _('Projects')
    app_name = 'projects'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['projects.urls']

@apphook_pool.register
class TASApphook(CMSApp):
    name = _('TAS')
    app_name = 'tas'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['tas.urls']

@apphook_pool.register
class ResourceDiscoveryApphook(CMSApp):
    name = _('Resource Discovery')
    app_name = 'g5k_discovery'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['g5k_discovery.urls']

@apphook_pool.register
class ApplianceCatalogApphook(CMSApp):
    name = _('Appliance Catalog')
    app_name = 'appliance_catalog'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['appliance_catalog.urls']

@apphook_pool.register
class SharingPortalApphook(CMSApp):
    name = _('Sharing Portal')
    app_name = 'sharing_portal'

    def get_urls(self, page=None, language=None, **kwargs):
        return ["sharing_portal.urls"]
