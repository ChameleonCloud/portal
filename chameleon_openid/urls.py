from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.openid_login, name='openid_login'),
    url(r'^callback/$', views.openid_callback, name='openid_callback'),
    url(r'^connect/$', views.openid_connect, name='openid_connect'),
    url(r'^register/$', views.openid_register, name='openid_register'),

    url(r'^geni/$', views.activate_geni, name='activate_geni'),
]
