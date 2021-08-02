from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _
from user_news.models import News, UserNewsPluginModel


@plugin_pool.register_plugin
class UserNewsPlugin(CMSPluginBase):
    model = UserNewsPluginModel
    name = _('User News')
    render_template = "user_news/cms/plugin.html"

    def render(self, context, instance, placeholder):
        context['instance'] = instance
        queryset = News.objects.order_by('-created')

        if not instance.display_events:
            queryset = queryset.filter(event__isnull=True)

        if not instance.display_outages:
            queryset = queryset.filter(outage__isnull=True)

        if not instance.display_news:
            queryset = queryset.exclude(outage__isnull=True, event__isnull=True)

        context['news_list'] = queryset[:instance.limit]

        return context


@plugin_pool.register_plugin
class UserNewsPagePlugin(CMSPluginBase):
    model = UserNewsPluginModel
    name = _('User News Page')
    render_template = "user_news/cms/plugin_page.html"

    def render(self, context, instance, placeholder):
        context['instance'] = instance

        queryset = News.objects.order_by('-created')

        if not instance.display_events:
            queryset = queryset.filter(event__isnull=True)

        if not instance.display_outages:
            queryset = queryset.filter(outage__isnull=True)

        if not instance.display_news:
            queryset = queryset.exclude(outage__isnull=True, event__isnull=True)

        paginator = Paginator(queryset, instance.limit)
        page = context['request'].GET.get('page')
        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            items =  paginator.page(paginator.num_pages)

        context['news_items'] = items

        return context
