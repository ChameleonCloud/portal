from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^webinar/(?P<id>\d+)/$', views.webinar, name='webinar'),
    url(r'^webinar/(?P<id>\d+)/register/$', views.register, name='register'),
    url(r'^webinar/(?P<id>\d+)/unregister/$', views.unregister, name='unregister'),
]
