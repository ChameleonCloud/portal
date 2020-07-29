from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^public$', views.index, {'collection': 'public'}, name='index_public'),
    url(r'^my$', views.index, {'collection': 'mine'}, name='index_mine'),
    url(r'^project/(?P<project_id>\d+)', views.index, {'collection': 'project'}, name='index_project'),
    url(r'^upload$', views.upload, name='upload'),
    url(r'^(?P<pk>\d+)$', views.artifact, name='detail'),
    url(r'^(?P<pk>\d+)/version/(?P<version_idx>\d+)', views.artifact, name='detail_version'),
    url(r'^(?P<pk>\d+)/edit$', views.edit_artifact, name='edit'),
    url(r'^(?P<pk>\d+)/edit/sync_versions$', views.sync_artifact_versions, name='sync_versions'),
    url(r'^edit$', views.edit_redirect, name='edit_redirect'),
    url(r'^edit/sync_versions$', views.sync_artifact_versions_redirect, name='sync_versions_redirect'),
]
