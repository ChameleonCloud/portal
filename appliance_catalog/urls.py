from django.conf.urls import patterns, url

urlpatterns = patterns(
    'appliance_catalog.views',
    url( r'^$', 'list', name='list' ),
    url( r'^create/$', 'create', name='create' ),
    url( r'^detail/(?P<pk>\d+)/$', 'detail', name='detail' ),
    url( r'^edit/(?P<pk>\d+)/$', 'edit', name='edit' ),
    url( r'^delete/(?P<pk>\d+)/$', 'delete', name='delete' ),
)
