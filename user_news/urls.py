from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from user_news.views import UserEventsListView, UserNewsListView, UserNewsDetailView, UserNewsRedirectView, UserNewsFeed, OutageListView, OutageDetailView, OutageFeed

urlpatterns = patterns('',
    url(r'^$', UserNewsListView.as_view(), name='list'),
    url(r'^rss/$', UserNewsFeed(), name='feed'),
    url(r'^events/$', UserEventsListView.as_view(), name='events_list'),

    url(r'^outages/$', OutageListView.as_view(), name='outage_list'),
    url(r'^outages/rss/$', OutageFeed(), name='outage_feed'),

    url(r'^(?P<slug>[-_\w]+)/$', UserNewsDetailView.as_view(), name='detail'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-_\w]+)/$',
        UserNewsRedirectView.as_view()
    ),
    url(r'^outages/(?P<slug>[-_\w]+)/$', OutageDetailView.as_view(), name='outage_detail'),
)
