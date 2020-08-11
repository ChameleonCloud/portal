from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index_all, name='index_all'),
    url(r'^public$', views.index_public, name='index_public'),
    url(r'^my$', views.index_mine, name='index_mine'),
    # url(r'^project/(?P<project_id>\d+)', views.index_project, name='index_project'),

    url(r'^(?P<pk>\d+)$', views.artifact, name='detail'),
    url(r'^(?P<pk>\d+)/version/(?P<version_idx>\d+)', views.artifact, name='detail_version'),
    url(r'^(?P<pk>\d+)/edit$', views.edit_artifact, name='edit'),
    url(r'^edit$', views.edit_redirect, name='edit_redirect'),

    # Deprecated
    url(r'^upload$', views.upload, name='upload'),
    url(r'^(?P<pk>\d+)/edit/sync_versions$', views.sync_artifact_versions, name='sync_versions'),
    url(r'^edit/sync_versions$', views.sync_artifact_versions_redirect, name='sync_versions_redirect'),

    url(r'^create/embed$', views.create_artifact_embed, name='create_embed'),
    url(r'^(?P<pk>\d+)/edit/embed$', views.edit_artifact_embed, name='edit_embed'),
]
