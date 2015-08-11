from cms.sitemaps import CMSSitemap
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse_lazy
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.conf import settings
from django.views.generic import RedirectView
from user_news.views import OutageListView, OutageDetailView, OutageFeed


urlpatterns = patterns('',

    # admin urls
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/impersonate/', include('impersonate.urls')),
    url(r'^admin/allocations/', include('allocations.urls', namespace='allocations_admin')),

    # contrib urls
    url(r'^openid/', include('chameleon_openid.urls', namespace='chameleon_openid')),
    url(r'^ckeditor/', include('ckeditor.urls')),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^terms/', include('termsandconditions.urls', namespace='terms')),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': {'cmspages': CMSSitemap}}),

    # custom urls
    url(r'^login/', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', { 'next_page': '/' }, name='logout'),
    url(r'^register/', RedirectView.as_view(url=reverse_lazy('tas:register'))),
    url(r'^user/', include('tas.urls', namespace='tas')),
    url(r'^email-confirmation/', 'tas.views.email_confirmation'),
    url(r'^password-reset/', 'tas.views.password_reset'),
    url(r'^user/dashboard/', 'chameleon.views.dashboard', name='dashboard'),
    url(r'^user/projects/', include('projects.urls', namespace='projects')),
    url(r'^user/outages/$', OutageListView.as_view(), name='outage_list'),
    url(r'^user/outages/rss/$', OutageFeed(), name='outage_feed'),
    url(r'^user/outages/(?P<slug>[-_\w]+)/$', OutageDetailView.as_view(), name='outage_detail'),
    url(r'^user/help/', include('djangoRT.urls', namespace='djangoRT')),
    url(r'^user/discovery/', include('g5k_discovery.urls', namespace='g5k_discovery')),
    url(r'^user/early-user-program/', include('cc_early_user_support.urls', namespace='cc_early_user_support')),
    url(r'^feed\.xml', RedirectView.as_view(url=reverse_lazy('user_news:feed'))),

    # mailing list resource for mailman autosubscribe
    url(r'^mailman/(?P<list_name>\w+)\.txt$', 'chameleon_mailman.views.mailman_export_list', name='mailman_export_list'),
    url(r'^user/profile/subscriptions/$', 'chameleon_mailman.views.manage_mailman_subscriptions', name='mailman_manage'),

    # cms urls
    url(r'^', include('cms.urls')),
)

if settings.DEBUG:
    urlpatterns = patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',  # NOQA
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        ) + staticfiles_urlpatterns() + urlpatterns  # NOQA
