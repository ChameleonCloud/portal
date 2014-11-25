
from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

from documentation import views

urlpatterns = patterns(
    'documentation.views',

    url(r'^$', 'display_doc' ),
    url(r'^(.*)/$', 'display_doc' ),
)
