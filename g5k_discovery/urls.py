from django.conf.urls import patterns, include, url
from g5k_discovery.views import DiscoveryView, g5k_json, g5k_html, node_view, node_data
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns = patterns('',
    url(r'^$', DiscoveryView.as_view(), name='discovery'),
    url(r'^node/(?P<resource>.+?)\.json/$', node_data, name='node_json'),
    url(r'^node/(?P<resource>.+?)/$', node_view, name='node_detail'),
    url(r'^(?P<resource>.+?)\.json$', g5k_json, name='discovery_json'),
    url(r'^template/(?P<resource>.+?)\.html/$', g5k_html, name='discovery_html'),
    #url(r'^(?P<resource>.+?)?/?$', DiscoveryView.as_view(), name='discovery'),
)
urlpatterns += staticfiles_urlpatterns()
