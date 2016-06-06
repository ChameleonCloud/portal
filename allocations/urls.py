from django.conf.urls import patterns, url

urlpatterns = patterns(
    'allocations.views',
    url( r'^$', 'index', name='index' ),
    url( r'^view/$', 'view', name='view' ),
    url( r'^approval/$', 'approval', name='approval' ),
    url( r'^denied/$', 'denied', name='denied' ),
    url( r'^user/$', 'user_select', name='user_select' ),
    url( r'^user/(?P<username>.+?)/$', 'user_projects', name='user_projects' ),
    url(r'^template/(?P<resource>.+?)\.html/$', 'allocations_template', name='allocations_template'),
)
