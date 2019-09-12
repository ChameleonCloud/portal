from cms.sitemaps import CMSSitemap
from chameleon import views as chameleon_views
from chameleon import os_login as chameleon_os_login
from chameleon_mailman import views as chameleon_mailman_views
from django.conf.urls import include, url
from django.core.urlresolvers import reverse_lazy
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.contrib.auth.views import logout
from django.conf import settings
from django.views.generic import RedirectView
from django.views.static import serve
from tas import views as tas_views
from user_news.views import OutageListView, OutageDetailView, OutageFeed
import views

urlpatterns = [
    # admin urls
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/impersonate/', include('impersonate.urls')),
    url(r'^admin/allocations/', include('allocations.urls',
                                        namespace='allocations_admin')),
    url(r'^admin/usage/', include('usage.urls', namespace='usage_admin')),

    # contrib urls
    url(r'^openid/', include('chameleon_openid.urls', namespace='chameleon_openid')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^terms/', include('termsandconditions.urls')),
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': {'cmspages': CMSSitemap}},
        name='django.contrib.sitemaps.views.sitemap'),

    # custom urls
    url(r'^login/', chameleon_os_login.custom_login, name='login'),
    url(r'^sso/horizon/$', chameleon_views.horizon_sso_login, name='horizon_sso_login'),
    url(r'^sso/horizon/unavailable', chameleon_views.horizon_sso_unavailable, name='horizon_sso_unavailable'),
    url(r'^logout/', logout, {'next_page': '/'}, name='logout'),

    url(r'^register/', RedirectView.as_view(permanent=True, url=reverse_lazy('tas:register'))),
    url(r'^user/', include('tas.urls', namespace='tas')),
    url(r'^email-confirmation/', tas_views.email_confirmation),
    url(r'^password-reset/', tas_views.password_reset),
    url(r'^forgot-username/$', tas_views.recover_username),

    url(r'^user/dashboard/', chameleon_views.dashboard, name='dashboard'),

    url(r'^appliances/', include('appliance_catalog.urls', namespace='appliance_catalog')),

    url(r'^share/', include('sharing_portal.urls', namespace='sharing_portal')),

    url(r'^news/', include('user_news.urls', namespace='user_news')),
    url(r'^feed\.xml', RedirectView.as_view(permanent=True, url=reverse_lazy('user_news:feed'))),
    url(r'^user/outages/$', OutageListView.as_view(), name='outage_list'),
    url(r'^user/outages/rss/$', OutageFeed(), name='outage_feed'),
    url(r'^user/outages/(?P<slug>[-_\w]+)/$', OutageDetailView.as_view(),
        name='outage_detail'),

    url(r'^hardware/', include('g5k_discovery.urls', namespace='hardware')),
    # Unclear if this legacy route still needs to be supported
    url(r'^user/discovery/', RedirectView.as_view(permanent=True, url=reverse_lazy('hardware:discovery'))),

    url(r'^user/projects/', include('projects.urls', namespace='projects')),

    url(r'^user/help/', include('djangoRT.urls', namespace='djangoRT')),

    url(r'^user/early-user-program/', include('cc_early_user_support.urls',
                                              namespace='cc_early_user_support')),

    url(r'^user/webinar/', include('webinar_registration.urls',
                                   namespace='webinar_registration')),

    # mailing list resource for mailman autosubscribe
    url(r'^mailman/new_members.txt$',
        chameleon_mailman_views.mailman_export_list, name='mailman_export_list'),

    # cms urls
    url(r'^taggit_autosuggest/', include('taggit_autosuggest.urls')),
    url(r'^', include('blog_comments.urls')),
    url(r'^', include('cms.urls')),
]

if settings.DEBUG:
    urlpatterns = [
        url(r'^media/(?P<path>.*)$', serve,  # NOQA
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    ] + staticfiles_urlpatterns() + urlpatterns  # NOQA
else:
    urlpatterns = staticfiles_urlpatterns() + urlpatterns
