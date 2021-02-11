from django.conf.urls import url

from . import views

urlpatterns = [
    url(r"^$", views.UserNewsListView.as_view(), name="list"),
    url(r"^rss/$", views.UserNewsFeed(), name="feed"),
    url(r"^outages/$", views.OutageListView.as_view(), name="outage_list"),
    url(r"^outages/rss/$", views.OutageFeed(), name="outage_feed"),
    url(r"^(?P<slug>[-_\w]+)/$", views.UserNewsDetailView.as_view(), name="detail"),
    url(
        r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-_\w]+)/$",
        views.UserNewsRedirectView.as_view(),
    ),
    url(
        r"^outages/(?P<slug>[-_\w]+)/$",
        views.OutageDetailView.as_view(),
        name="outage_detail",
    ),
]
