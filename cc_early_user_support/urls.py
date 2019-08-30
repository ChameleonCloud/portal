from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^program/(?P<id>\d+)/$', views.view_program, name='program'),
    url(r'^program/(?P<id>\d+)/participate/$', views.request_to_participate, name='participate'),
    url(r'^program/(?P<id>\d+)/export_participants\.txt', views.participants_export_list),
    url(r'^program/(?P<id>\d+)/export_participants/(?P<list_type>\w+)\.txt', views.participants_export_list),
]
