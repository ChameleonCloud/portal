from django.conf.urls import patterns, include, url
from . import views

urlpatterns = patterns('',
    url( r'^$', views.user_projects, name='user_projects' ),
    url( r'^new/$', views.create_project, name='create_project' ),
    url( r'^new/allocation/(\d+)/$', views.create_allocation, name='create_allocation'),
    url( r'^new/allocation/(\d+)/(\d+)$', views.create_allocation, name='renew_allocation'),
    url( r'^(\d+)/$', views.view_project, name='view_project' ),
    url( r'^futuregrid/$', views.lookup_fg_projects, name='lookup_fg_projects' ),
    url( r'^futuregrid/(\d+)/migrate/$', views.fg_project_migrate, name='fg_project_migrate' ),
    url( r'^(\d+)/fg_add_user/$', views.fg_add_user, name='fg_add_user' ),
)
