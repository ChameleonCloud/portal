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
from django.urls import reverse, reverse_lazy, path, re_path
from user_news.views import OutageDetailView, OutageFeed, OutageListView

from chameleon import os_login as chameleon_os_login
from chameleon import views as chameleon_views

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
        path("admin/login/", AdminOIDCLogin.as_view()),
        re_path(r"^admin/impersonate/(?!impersonationlog/)", include("impersonate.urls")),
        path(
            "admin/allocations/",
            include("allocations.urls", namespace="allocations_admin"),
        ),
        path("admin/", admin.site.urls),
        # contrib urls
        path("oidc/", include("mozilla_django_oidc.urls")),
        path("ckeditor/", include("ckeditor_uploader.urls")),
        path("terms/", include("termsandconditions.urls")),
        path(
            "sitemap.xml",
            sitemap,
            {"sitemaps": {"cmspages": CMSSitemap}},
            name="django.contrib.sitemaps.views.sitemap",
        ),
        # custom urls
        path("login/", chameleon_os_login.custom_login, name="login"),
        path("logout/", chameleon_os_login.custom_logout, name="logout"),
        path("register/", chameleon_views.OIDCRegisterView.as_view(), name="register"),
        # Rollout endpoints for new login
        path(
            "auth/force-password-login/",
            chameleon_views.force_password_login,
            name="force_password_login",
        ),
        path(
            "auth/confirm/",
            chameleon_os_login.confirm_legacy_credentials,
            name="federation_confirm_legacy_credentials",
        ),
        path(
            "user/migrate/",
            chameleon_views.migrate,
            name="federation_migrate_account",
        ),
        path("api/user/migrate/status/", chameleon_views.api_migration_state),
        path("api/user/migrate/job/", chameleon_views.api_migration_job),
        # Legacy account endpoints
        path("user/", include("tas.urls", namespace="tas")),
        path("password-reset/", chameleon_views.password_reset),
        path("user/dashboard/", chameleon_views.dashboard, name="dashboard"),
        path(
            "feed.xml",
            RedirectView.as_view(permanent=True, url=reverse_lazy("user_news:feed")),
        ),
        path("user/outages/", OutageListView.as_view(), name="outage_list"),
        path("user/outages/rss/", OutageFeed(), name="outage_feed"),
        path(
            "user/outages/<slug:slug>/",
            OutageDetailView.as_view(),
            name="outage_detail",
        ),
        path("hardware/", include("g5k_discovery.urls", namespace="hardware")),
        # Unclear if this legacy route still needs to be supported
        path(
            "user/discovery/",
            RedirectView.as_view(
                permanent=True, url=reverse_lazy("hardware:discovery")
            ),
        ),
        path("user/projects/", include("projects.urls", namespace="projects")),
        path("user/help/", include("djangoRT.urls", namespace="djangoRT")),
        path(
            "user/webinar/",
            include("webinar_registration.urls", namespace="webinar_registration"),
        ),
        # mailing list resource for mailman autosubscribe
        path(
            "mailman/new_members.txt",
            chameleon_mailman_views.mailman_export_list,
            name="mailman_export_list",
        ),
        # ensure default djangocms_blog namespace is registered at /blog
        # (the auto-setup hook doesn't work well if the page is moved in the hierarchy)
        path("blog/", include("djangocms_blog.urls", namespace="Blog")),
        # robots.txt
        path(
            "robots.txt",
            TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        ),
        # cms urls
        path("taggit_autosuggest/", include("taggit_autosuggest.urls")),
        path("", include("blog_comments.urls")),
        path("", include("cms.urls")),
        # /appliances is bound to appliance_catalog app via CMS integration
        # /share is bound to sharing_portal app via CMS integration
        # /news is bound to user_news app via CMS integration
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)

