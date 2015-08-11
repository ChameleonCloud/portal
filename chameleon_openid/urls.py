from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'chameleon_openid.views.openid_login', name='openid_login'),
    url(r'^callback/$', 'chameleon_openid.views.openid_callback', name='openid_callback'),
    )