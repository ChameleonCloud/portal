
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import login, logout

import chameleon.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'chameleon.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', chameleon.views.home, name='home'),

    url(r'^accounts/login/$', login),
    url(r'^accounts/logout/$', logout, {'next_page' : '/'}),
    url(r'^accounts/password_reset/', include('password_reset.urls')),

    url(r'helpdesk/', include('helpdesk.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^about/', include('about.urls')),
    url(r'^status/', include('status.urls')),
    url(r'^news/', include('news.urls')),

    url(r'^documentation/', include('documentation.urls')),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# password reset starts at accounts/password_reset/recover/
