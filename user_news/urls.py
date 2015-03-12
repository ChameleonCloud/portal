from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from user_news.views import UserNewsListView, UserNewsDetailView, UserNewsRedirectView

urlpatterns = patterns('',
    url(r'^$', UserNewsListView.as_view(), name='list'),
    url(r'^(?P<slug>[-_\w]+)/$', UserNewsDetailView.as_view(), name='detail'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-_\w]+)/$',
        UserNewsRedirectView.as_view()
    ),
)
