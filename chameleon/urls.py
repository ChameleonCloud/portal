from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from django.contrib import admin


import chameleon.views

urlpatterns = patterns(
    '',

    url(r'^$', 'chameleon.views.home', name='home'),
    url(r'^login/', 'django.contrib.auth.views.login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', { 'next_page': '/' }),
    url(r'^register/', RedirectView.as_view(url=reverse_lazy('register'))),
    url(r'^email-confirmation', 'tas.views.email_confirmation'),
    url(r'^password-reset', 'tas.views.password_reset'),
    url(r'^user/', include('tas.urls')),
    url(r'^user/dashboard/', 'chameleon.views.dashboard', name='dashboard'),
    url(r'^user/projects/', include('projects.urls')),
    url(r'^help/', include('djangoRT.urls')),
    url(r'^documentation/', include('documentation.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^captcha/', include('captcha.urls')),

    # content urls
    url( r'^about/$', 'github_content.views.about'),
    url( r'^news/$', 'github_content.views.news'),
    url( r'^news/', include('github_content.urls')),
    url( r'^NSFCloudWorkshop/', RedirectView.as_view(url=reverse_lazy('github_content.views.nsf_cloud_workshop'))),
    url( r'^nsf-cloud-workshop/$', 'github_content.views.nsf_cloud_workshop'),
    url( r'^nsf-cloud-workshop/NSFCloud Workshop Tentative Agenda.pdf$', 'github_content.views.nsf_cloud_workshop_agenda'),
)
