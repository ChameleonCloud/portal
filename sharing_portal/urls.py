from django.urls import path
from . import views

app_name = "sharing_portal"

urlpatterns = [
    path("", views.index_all, name="index_all"),
    path("public", views.index_public, name="index_public"),
    path("my", views.index_mine, name="index_mine"),
    path("<uuid:pk>", views.artifact, name="detail"),
    path("<uuid:pk>/launch", views.launch, name="launch"),
    path("<uuid:pk>/request", views.request_daypass, name="request_daypass"),
    path("requests/", views.list_daypass_requests, name="list_daypass_requests"),
    path("requests/<int:request_id>", views.review_daypass, name="review_daypass"),
    path(
        "<uuid:pk>/version/<version_slug>",
        views.artifact,
        name="detail_version",
    ),
    path(
        "<uuid:pk>/version/<version_slug>/launch",
        views.launch,
        name="launch_version",
    ),
    path("<uuid:pk>/edit", views.edit_artifact, name="edit"),
    path("<uuid:pk>/share", views.share_artifact, name="share"),
]
