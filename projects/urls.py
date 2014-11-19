from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'projects.views',

    url( r'^$', 'user_projects', name='user_projects' ),

    url( r'^new/$', 'create_project', name='create_project' ),

    url( r'^(\d+)/$', 'view_project', name='view_project' ),

    url( r'^futuregrid/$', 'lookup_fg_projects', name='lookup_fg_projects' ),

    url( r'^futuregrid/migrate$', 'fg_project_migrate', name='fg_project_migrate' ),
)
