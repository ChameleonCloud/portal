from django.conf.urls import url
from . import views

app_name = "g5k_discovery"

urlpatterns = [
    url(r'^', views.index, name='discovery'),
    url(r'^node/(?P<resource>.+?)\.json/', views.node_data, name='node_json'),
    url(r'^node/(?P<resource>.+?)/', views.node_view, name='node_detail'),
    url(r'^(?P<resource>.+?)\.json', views.g5k_json, name='discovery_json'),
    url(r'^template/(?P<resource>.+?)\.html/', views.g5k_html, name='discovery_html'),
]
