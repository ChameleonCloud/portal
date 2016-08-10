from django.conf.urls import patterns, url
from .views import ApplianceDeleteView
urlpatterns = patterns(
    'appliance_catalog.views',
    url(r'^$', 'app_list', name='app_list'),
    url(r'^(?P<pk>\d+)/$', 'app_detail', name='app_detail'),
    url(r'^(?P<pk>\d+)/docs/$', 'app_documentation', name='app_documentation'),
    url(r'^(?P<pk>\d+)/edit/$', 'app_edit', name='app_edit'),
    url(r'^(?P<pk>\d+)/delete/$', ApplianceDeleteView.as_view(), name='app_delete'),
    url(r'^create/$', 'app_create', name='app_create'),
    url(r'^template/(?P<resource>.+?)\.html/$', 'app_template', name='app_template'),
	url(r'^api/appliances/$', 'get_appliances', name='get_appliances'),
	url(r'^api/appliances/(?P<pk>\d+)/$', 'get_appliance', name='get_appliance'),
    url(r'^api/appliances/(?P<pk>\d+)/template$', 'get_appliance_template', name='get_appliance_template'),
	url(r'^api/keywords/$', 'get_keywords', name='get_keywords'),
	url(r'^api/keywords/(?P<appliance_id>\d+)/$', 'get_keywords', name='get_keywords'),

)
