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
