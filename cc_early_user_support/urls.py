from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'cc_early_user_support.views',
    url(r'^$', 'index', name='index'),
    url(r'^request/$', 'request_early_user', name='request'),
)
