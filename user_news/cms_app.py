from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

@apphook_pool.register
class UserNewsApphook(CMSApp):
    name = _('User News Apphook')
    urls = ['user_news.urls']
    app_name = 'user_news'
