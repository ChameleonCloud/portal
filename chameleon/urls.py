
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin

#import openstack_auth.views

import chameleon.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'chameleon.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', chameleon.views.home, name='home'),

    url(r'^about/', include('about.urls')),
    url(r'^news/', include('news.urls')),
    url(r'^documentation/', include('documentation.urls')),
    url(r'helpdesk/', include('helpdesk.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^user/', include('user.urls')),
    url(r'^allocation/', include('allocation.urls')),

    url(r'^status/', include('status.urls')),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
