from django.urls import re_path
from . import views

app_name = "sharing_portal"

urlpatterns = [
    re_path(r"^$", views.index_all, name="index_all"),
    re_path(r"^public$", views.index_public, name="index_public"),
    re_path(r"^my$", views.index_mine, name="index_mine"),
    re_path(
        r"^project/(?P<charge_code>[\w-]+)$", views.index_project, name="index_project"
    ),
    re_path(r"^(?P<pk>\d+)$", views.artifact, name="detail"),
    re_path(r"^(?P<pk>\d+)/launch$", views.launch, name="launch"),
    re_path(
        r"^(?P<pk>\d+)/version/(?P<version_idx>\d+)$",
        views.artifact,
        name="detail_version",
    ),
    re_path(
        r"^(?P<pk>\d+)/version/(?P<version_idx>\d+)/launch$",
        views.launch,
        name="launch_version",
    ),
    re_path(r"^(?P<pk>\d+)/edit$", views.edit_artifact, name="edit"),
    re_path(r"^(?P<pk>\d+)/share$", views.share_artifact, name="share"),
    re_path(r"^create/embed$", views.embed_create, name="embed_create"),
    re_path(r"^(?P<pk>\d+)/edit/embed$", views.embed_edit, name="embed_edit"),
    re_path(r"^edit/cancel/embed$", views.embed_cancel, name="embed_cancel"),
]
