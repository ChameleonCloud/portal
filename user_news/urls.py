from django.conf.urls import patterns, include, url
from user_news.views import UserNewsListView, UserNewsDetailView

urlpatterns = patterns('',
    url(r'^$', UserNewsListView.as_view(), name='list'),
    url(r'^(?P<slug>[-_\w]+)/$', UserNewsDetailView.as_view(), name='detail'),
)
