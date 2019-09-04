from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

@apphook_pool.register
class UserNewsApphook(CMSApp):
    name = _('User News')
    app_name = 'user_news'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['user_news.urls']
