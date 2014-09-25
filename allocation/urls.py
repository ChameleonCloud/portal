
from django.conf import settings
from django.conf.urls import patterns, include, url

import allocation.views

urlpatterns = patterns('',
    url(r'^request/$', allocation.views.request_allocation),
    url(r'^request/thanks/$', allocation.views.request_thanks),

    url(r'^review/$', allocation.views.allocation_requests),
    url(r'^review/approved/$', allocation.views.approve_request),
    url(r'^review/denied/$', allocation.views.deny_request),
    url(r'^review/request/(?P<id>\S+)/$', allocation.views.approve_allocation),
)
