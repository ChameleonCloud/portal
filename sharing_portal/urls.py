from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^upload$', views.upload, name='upload'),
    url(r'^(?P<pk>\d+)$', views.DetailView.as_view(), name='detail'),
    url(r'^(?P<pk>\d+)/edit$', views.edit_artifact, name='edit'),
]
