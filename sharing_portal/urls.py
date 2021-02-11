from django.conf.urls import url

from . import views

app_name = "sharing_portal"

urlpatterns = [
    url(r"^", views.index_all, name="index_all"),
    url(r"^public", views.index_public, name="index_public"),
    url(r"^my", views.index_mine, name="index_mine"),
    url(r"^project/(?P<charge_code>[\w-]+)", views.index_project, name="index_project"),
    url(r"^(?P<pk>\d+)", views.artifact, name="detail"),
    url(r"^(?P<pk>\d+)/launch", views.launch, name="launch"),
    url(
        r"^(?P<pk>\d+)/version/(?P<version_idx>\d+)$",
        views.artifact,
        name="detail_version",
    ),
    url(
        r"^(?P<pk>\d+)/version/(?P<version_idx>\d+)/launch$",
        views.launch,
        name="launch_version",
    ),
    url(r"^(?P<pk>\d+)/edit", views.edit_artifact, name="edit"),
    url(r"^(?P<pk>\d+)/share", views.share_artifact, name="share"),
    url(r"^create/embed", views.embed_create, name="embed_create"),
    url(r"^(?P<pk>\d+)/edit/embed", views.embed_edit, name="embed_edit"),
    url(r"^edit/cancel/embed", views.embed_cancel, name="embed_cancel"),
]
