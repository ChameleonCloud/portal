from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'projects.views',

    url( r'^$', 'user_projects', name='user_projects' ),

    url( r'^new/$', 'create_project', name='create_project' ),
)
