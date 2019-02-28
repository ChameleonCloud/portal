from django.conf.urls import patterns, include, url
from . import views

urlpatterns = patterns('',
    url( r'^$', views.user_projects, name='user_projects' ),
    url( r'^new/$', views.create_project, name='create_project' ),
    url( r'^(\d+)/$', views.view_project, name='view_project' ),
    url( r'^(\d+)/allocation/$', views.create_allocation, name='create_allocation'),
    url( r'^(\d+)/allocation/(\d+)$', views.create_allocation, name='renew_allocation'),
    url(r'^edit/nickname/$', views.edit_nickname, name='edit_nickname'),
    url(r'^api/extras/$', views.get_extras, name='get_extras'),
)
