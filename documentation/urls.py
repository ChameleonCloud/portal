
from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

from documentation import views

urlpatterns = patterns('',
    url(r'\S*', views.doc, name='doc'),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
