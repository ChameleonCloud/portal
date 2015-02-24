from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _
from user_news.cms_models import UserNewsPluginModel
from user_news.models import News

@plugin_pool.register_plugin
class UserNewsPlugin(CMSPluginBase):
    model = UserNewsPluginModel
    name = _('User News')
    render_template = "user_news/cms/plugin.html"

    def render(self, context, instance, placeholder):
        context['instance'] = instance

        context['news_list'] = News.objects.order_by('-created')[:instance.limit]

        return context
