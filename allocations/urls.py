from django.conf.urls import patterns, url

urlpatterns = patterns(
    'allocations.views',
    url( r'^view/$', 'view', name='view' ),
    url( r'^index/$', 'index', name='index' ),
    url( r'^approval/$', 'approval', name='approval' ),
    url(r'^template/(?P<resource>.+?)\.html/$', 'allocations_template', name='allocations_template'),
)
