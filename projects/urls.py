from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.user_projects, name='user_projects'),
    url(r'^new/$', views.create_project, name='create_project'),
    url(r'^(\d+)/$', views.view_project, name='view_project'),
    url(r'^(\d+)/allocation/$', views.create_allocation, name='create_allocation'),
    url(r'^(\d+)/allocation/(\d+)$', views.create_allocation, name='renew_allocation'),
    url(r'^api/extras/$', views.get_extras, name='get_extras'),
]
