from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns(
    'github_content.views',

    url( r'^about/$', 'about' ),
    url( r'^news/$', 'news' ),
    url( r'^news/(\d+)/(\d+)/(\d+)/(.*)/$', 'news_story' ),
    url( r'^talks/$', 'talks' ),
    url( r'^talks/(.*)/$', 'talks_attachment' ),
    url( r'^NSFCloudWorkshop/', RedirectView.as_view( url=reverse_lazy( 'github_content.views.nsf_cloud_workshop' ) ) ),
    url( r'^nsf-cloud-workshop/$', 'nsf_cloud_workshop' ),
    url( r'^nsf-cloud-workshop/(.*)$', 'nsf_cloud_workshop_attachment' ),
)
