
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin

import chameleon.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'chameleon.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', chameleon.views.home, name='home'),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page' : '/'}),

    #(r'helpdesk/', include('helpdesk.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^about/', include('about.urls')),
    url(r'^status/', include('status.urls')),
    url(r'^news/', include('news.urls')),

    url(r'^documentation/', include('documentation.urls')),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
