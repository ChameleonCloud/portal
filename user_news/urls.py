from django.urls import path
from . import views

app_name = "user_news"

urlpatterns = [
    path("/", views.UserNewsListView.as_view(), name="list"),
    path("rss/", views.UserNewsFeed(), name="feed"),
    path("outages/", views.OutageListView.as_view(), name="outage_list"),
    path("outages/rss/", views.OutageFeed(), name="outage_feed"),
    path("<slug:slug>/", views.UserNewsDetailView.as_view(), name="detail"),
    path(
        "<int:year>/<int:month>/<int:day>/<slug:slug>/",
        views.UserNewsRedirectView.as_view(),
    ),
    path(
        "outages/<slug:slug>/",
        views.OutageDetailView.as_view(),
        name="outage_detail",
    ),
]
