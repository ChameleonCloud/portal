from django.urls import path
from . import views

app_name = "sharing_portal"

urlpatterns = [
    path("", views.index_all, name="index_all"),
    path("public", views.index_public, name="index_public"),
    path("my", views.index_mine, name="index_mine"),
    path("project/<str:charge_code>", views.index_project, name="index_project"),
    path("<int:pk>", views.artifact, name="detail"),
    path("<int:pk>/launch", views.launch, name="launch"),
    path("<int:pk>/request", views.request_day_pass, name="request_day_pass"),
    path("list_requests", views.list_day_pass_requests, name="list_day_pass_requests"),
    path("requests/<int:request_id>", views.review_day_pass, name="review_day_pass"),
    path(
        "<int:pk>/version/<int:version_idx>",
        views.artifact,
        name="detail_version",
    ),
    path(
        "<int:pk>/version/<int:version_idx>/launch",
        views.launch,
        name="launch_version",
    ),
    path("<int:pk>/edit", views.edit_artifact, name="edit"),
    path("<int:pk>/share", views.share_artifact, name="share"),
    path("create/embed", views.embed_create, name="embed_create"),
    path("<int:pk>/edit/embed", views.embed_edit, name="embed_edit"),
    path("edit/cancel/embed", views.embed_cancel, name="embed_cancel"),
]
