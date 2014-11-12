from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from django.contrib import admin


import chameleon.views

urlpatterns = patterns(
    '',

    url(r'^$', 'chameleon.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    # url(r'^account/', include('django.contrib.auth.urls')),
    url(r'^login/', 'django.contrib.auth.views.login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', { 'next_page': '/' }),
    url(r'^register/', RedirectView.as_view(url=reverse_lazy('register'))),
    url(r'^user/', include('tas.urls')),
    url(r'^user/dashboard/', 'chameleon.views.dashboard', name='dashboard'),
    url(r'^help/', include('djangoRT.urls')),
    url(r'^documentation/', include('documentation.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
