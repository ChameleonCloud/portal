from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.views.generic.base import RedirectView
from django.contrib.syndication.views import Feed
from user_news.models import News, Event, Outage, OutageUpdate
from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER


class UserNewsListView(ListView):
    model = News
    paginate_by = 10
    queryset = News.objects.filter(outage__isnull=True, event__isnull=True).order_by(
        "-created"
    )


class UserNewsDetailView(DetailView):
    model = News

    def get_context_data(self, **kwargs):
        context = super(UserNewsDetailView, self).get_context_data(**kwargs)
        admin_menu = self.request.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        user_news_menu = admin_menu.get_or_create_menu(
            "user_news-menu", _("User News ...")
        )
        if user_news_menu:
            user_news_menu.add_modal_item(
                _('Edit Item "{0}"').format(context["news"].title),
                url=reverse("admin:user_news_news_change", args=[context["news"].id]),
                position=0,
            )
            user_news_menu.add_break(position=1)

        return context


class UserNewsRedirectView(RedirectView):
    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse("user_news:detail", args=[kwargs["slug"]])


class UserNewsFeed(Feed):
    title = "Chameleon News and Announcements"
    description = "News and Announcements related to the Chameleon Project."

    def link(self):
        return reverse("user_news:list")

    def items(self):
        return News.objects.filter(outage__isnull=True, event__isnull=True).order_by(
            "-created"
        )[:10]

    def item_title(self, item):
        return item.title

    def item_pubdate(self, item):
        return item.created

    def item_description(self, item):
        return item.summary

    def item_link(self, item):
        return reverse("user_news:detail", args=[item.slug])


class OutageListView(ListView):
    model = Outage
    paginate_by = 10
    queryset = Outage.objects.order_by("-created")


class OutageDetailView(DetailView):
    model = Outage

    def get_context_data(self, **kwargs):
        context = super(OutageDetailView, self).get_context_data(**kwargs)
        admin_menu = self.request.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        user_news_menu = admin_menu.get_or_create_menu(
            "user_news-menu", _("User News ...")
        )
        if user_news_menu:
            user_news_menu.add_modal_item(
                _('Edit Item "{0}"').format(context["outage"].title),
                url=reverse(
                    "admin:user_news_outage_change", args=[context["outage"].id]
                ),
                position=0,
            )
            user_news_menu.add_break(position=1)

        return context


class OutageFeed(UserNewsFeed):
    title = "Chameleon Outage Announcements"
    description = "Outage Announcements related to the Chameleon Project."

    def link(self):
        return reverse("user_news:outage_list")

    def items(self):
        return Outage.objects.order_by("-created")[:10]

    def item_description(self, item):
        description = "<p>Outage Start: %s<br>Expected Outage End: %s</p>%s" % (
            item.start_date.strftime("%Y-%m-%d %H:%M"),
            item.end_date.strftime("%Y-%m-%d %H:%M"),
            item.summary,
        )
        return description

    def item_link(self, item):
        return reverse("user_news:outage_detail", args=[item.slug])
