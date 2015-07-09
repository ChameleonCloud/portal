from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'cc_early_user_support.views',
    url(r'^$', 'index', name='index'),
    url(r'^program/(?P<id>\d+)/$', 'view_program', name='program'),
    url(r'^program/(?P<id>\d+)/participate/$', 'request_to_participate', name='participate'),
    url(r'^program/(?P<id>\d+)/export_participants\.txt', 'participants_export_list'),
    url(r'^program/(?P<id>\d+)/export_participants/(?P<list_type>\w+)\.txt', 'participants_export_list'),
)
