import logging

from chameleon_mailman import views as chameleon_mailman_views
from cms.sitemaps import CMSSitemap
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponseRedirect
from django.views import View
from django.views.generic import RedirectView, TemplateView
from django.urls import reverse, reverse_lazy, re_path, path
from user_news.views import OutageDetailView, OutageFeed, OutageListView

from chameleon import os_login as chameleon_os_login
from chameleon import views as chameleon_views

import allocations.urls
import impersonate.urls

logger = logging.getLogger(__name__)


class AdminOIDCLogin(View):
    """Overrides default login view to perform login via OIDC."""

    def get(self, request, **kwargs):
        url = reverse("oidc_authentication_init")
        if REDIRECT_FIELD_NAME in request.GET:
            url += f"?{REDIRECT_FIELD_NAME}={request.GET[REDIRECT_FIELD_NAME]}"
        return HttpResponseRedirect(url)


urlpatterns = (
    [
        # admin urls
        re_path(r"^admin/login/", AdminOIDCLogin.as_view()),
        path("admin/impersonate/", include("impersonate.urls")),
        path(
            "admin/allocations/",
            include("allocations.urls", namespace="allocations_admin"),
        ),
        re_path(r"^admin/", admin.site.urls),
        # contrib urls
        re_path(r"^oidc/", include("mozilla_django_oidc.urls")),
        re_path(r"^ckeditor/", include("ckeditor_uploader.urls")),
        re_path(r"^terms/", include("termsandconditions.urls")),
        re_path(
            r"^sitemap\.xml$",
            sitemap,
            {"sitemaps": {"cmspages": CMSSitemap}},
            name="django.contrib.sitemaps.views.sitemap",
        ),
        # custom urls
        re_path(r"^login/", chameleon_os_login.custom_login, name="login"),
        re_path(r"^logout/", chameleon_os_login.custom_logout, name="logout"),
        re_path(r"^register/", chameleon_views.OIDCRegisterView.as_view(), name="register"),
        # Rollout endpoints for new login
        re_path(
            r"^auth/force-password-login/$",
            chameleon_views.force_password_login,
            name="force_password_login",
        ),
        re_path(
            r"^auth/confirm/$",
            chameleon_os_login.confirm_legacy_credentials,
            name="federation_confirm_legacy_credentials",
        ),
        re_path(
            r"^user/migrate/$",
            chameleon_views.migrate,
            name="federation_migrate_account",
        ),
        re_path(r"^api/user/migrate/status/$", chameleon_views.api_migration_state),
        re_path(r"^api/user/migrate/job/$", chameleon_views.api_migration_job),
        # Legacy account endpoints
        re_path(r"^user/", include("tas.urls", namespace="tas")),
        re_path(r"^password-reset/$", chameleon_views.password_reset),
        re_path(r"^user/dashboard/", chameleon_views.dashboard, name="dashboard"),
        re_path(
            r"^feed\.xml",
            RedirectView.as_view(permanent=True, url=reverse_lazy("user_news:feed")),
        ),
        re_path(r"^user/outages/$", OutageListView.as_view(), name="outage_list"),
        re_path(r"^user/outages/rss/$", OutageFeed(), name="outage_feed"),
        re_path(
            r"^user/outages/(?P<slug>[-_\w]+)/$",
            OutageDetailView.as_view(),
            name="outage_detail",
        ),
        re_path(r"^hardware/", include("g5k_discovery.urls", namespace="hardware")),
        # Unclear if this legacy route still needs to be supported
        re_path(
            r"^user/discovery/",
            RedirectView.as_view(
                permanent=True, url=reverse_lazy("hardware:discovery")
            ),
        ),
        re_path(r"^user/projects/", include("projects.urls", namespace="projects")),
        re_path(r"^user/help/", include("djangoRT.urls", namespace="djangoRT")),
        re_path(
            r"^user/early-user-program/",
            include("cc_early_user_support.urls", namespace="cc_early_user_support"),
        ),
        re_path(
            r"^user/webinar/",
            include("webinar_registration.urls", namespace="webinar_registration"),
        ),
        # mailing list resource for mailman autosubscribe
        re_path(
            r"^mailman/new_members.txt$",
            chameleon_mailman_views.mailman_export_list,
            name="mailman_export_list",
        ),
        # ensure default djangocms_blog namespace is registered at /blog
        # (the auto-setup hook doesn't work well if the page is moved in the hierarchy)
        re_path(r"^blog/", include("djangocms_blog.urls", namespace="Blog")),
        # robots.txt
        re_path(
            r"^robots.txt$",
            TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        ),
        # cms urls
        re_path(r"^taggit_autosuggest/", include("taggit_autosuggest.urls")),
        re_path(r"^", include("blog_comments.urls")),
        re_path(r"^", include("cms.urls")),
        # /appliances is bound to appliance_catalog app via CMS integration
        # /share is bound to sharing_portal app via CMS integration
        # /news is bound to user_news app via CMS integration
    ]
    # + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)

