from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns(
    'github_content.views',

    url( r'^(\d+)/(\d+)/(\d+)/(.*)/', 'news_story'),
)
