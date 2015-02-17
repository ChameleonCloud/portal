from django.conf.urls import patterns, url

from djangoRT import views

urlpatterns = patterns('',
		url(r'^$', views.mytickets, name='mytickets'),
		url(r'^ticket/(?P<ticketId>\d+)/$', views.ticketdetail, name='detail'),
		url(r'^ticket/new/$', views.ticketcreate, name='create'),
		url(r'^ticket/reply/(?P<ticketId>\d+)/$', views.ticketreply, name='reply'),
		url(r'^ticket/close/(?P<ticketId>\d+)/$', views.ticketclose, name='close'),
		url(r'^ticket/new/guest$', views.ticketcreateguest, name='createguest'),
)
