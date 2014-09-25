
from django.conf import settings
from django.conf.urls import patterns, include, url

import allocation.views

urlpatterns = patterns('',
    url(r'^$', allocation.views.index),
    url(r'^granted/(?P<id>\S+)/$', allocation.views.allocation_view),

    url(r'^request/$', allocation.views.allocation_request_edit),
    url(r'^request/thanks/$', allocation.views.allocation_request_thanks),
    url(r'^request/view/(?P<id>\S+)/$', allocation.views.allocation_request_view),
    url(r'^request/(?P<id>\S+)/$', allocation.views.allocation_request_continue),

    url(r'^review/$', allocation.views.allocation_requests),
    url(r'^review/approved/$', allocation.views.approve_request),
    url(r'^review/denied/$', allocation.views.deny_request),
    url(r'^review/request/(?P<id>\S+)/$', allocation.views.approve_allocation),
)
