from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.app_list, name='app_list'),
    url(r'^(?P<pk>\d+)/$', views.app_detail, name='app_detail'),
    url(r'^(?P<pk>\d+)/docs/$', views.app_documentation, name='app_documentation'),
    url(r'^(?P<pk>\d+)/edit/$', views.app_edit, name='app_edit'),
    url(r'^(?P<pk>\d+)/edit/image/$', views.app_edit_image, name='app_edit_image'),
    url(r'^(?P<pk>\d+)/delete/$', views.ApplianceDeleteView.as_view(), name='app_delete'),
    url(r'^create/$', views.app_create, name='app_create'),
    url(r'^create/image/$', views.app_create_image, name='app_create_image'),
    url(r'^template/(?P<resource>.+?)\.html/$', views.app_template, name='app_template'),
    url(r'^api/appliances/$', views.get_appliances, name='get_appliances'),
    url(r'^api/appliances/uuid/$', views.get_published_appliances_uuid, name='get_published_appliances_uuid'),
    url(r'^api/appliances/(?P<pk>\d+)/$', views.get_appliance, name='get_appliance'),
    url(r'^api/appliances/appliance_id/(?P<appliance_id>[0-9a-f-]+)/$', views.get_appliance_by_id, name='get_appliance_by_id'),
    url(r'^api/appliances/(?P<pk>\d+)/template$', views.get_appliance_template, name='get_appliance_template'),
    url(r'^api/keywords/$', views.get_keywords, name='get_keywords'),
    url(r'^api/keywords/(?P<appliance_id>\d+)/$', views.get_keywords, name='get_keywords'),
]
