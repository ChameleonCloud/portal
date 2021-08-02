from django.urls import re_path
from . import views

app_name = "user_news"

urlpatterns = [
    re_path(r"^$", views.UserNewsListView.as_view(), name="list"),
    re_path(r"^rss/$", views.UserNewsFeed(), name="feed"),
    re_path(r"^outages/$", views.OutageListView.as_view(), name="outage_list"),
    re_path(r"^outages/rss/$", views.OutageFeed(), name="outage_feed"),
    re_path(r"^(?P<slug>[-_\w]+)/$", views.UserNewsDetailView.as_view(), name="detail"),
    re_path(
        r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[-_\w]+)/$",
        views.UserNewsRedirectView.as_view(),
    ),
    re_path(
        r"^outages/(?P<slug>[-_\w]+)/$",
        views.OutageDetailView.as_view(),
        name="outage_detail",
    ),
]
