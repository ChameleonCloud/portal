
from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

from news import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^announcement/$', views.announcements, name='announcements'),
    url(r'^announcement/(?P<pk>\S+)/$', views.AnnouncementView.as_view(), name='announcement'),
    url(r'^event/$', views.events, name='events'),
    url(r'^event/(?P<pk>\S+)/$', views.EventView.as_view(), name='event'),
    url(r'^outage/$', views.outages, name='outages'),
    url(r'^outage/(?P<pk>\S+)/$', views.OutageView.as_view(), name='outage'),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
