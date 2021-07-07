import logging

from chameleon_mailman import views as chameleon_mailman_views
from cms.sitemaps import CMSSitemap
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sitemaps.views import sitemap
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.views import View
from django.views.generic import RedirectView, TemplateView
from dynamic_rest import routers
from user_news.views import OutageDetailView, OutageFeed, OutageListView
from util.dynamic_drf_api import (
    AllocationViewSet,
    FieldViewSet,
    ProjectViewSet,
    TypeViewSet,
    UserViewSet,
)

from chameleon import os_login as chameleon_os_login
from chameleon import views as chameleon_views

logger = logging.getLogger(__name__)

router = routers.DynamicRouter()
router.register(r"api/projects", ProjectViewSet)
router.register(r"api/users", UserViewSet)
router.register(r"api/allocations", AllocationViewSet)
router.register(r"api/types", TypeViewSet)
router.register(r"api/fields", FieldViewSet)

logger.debug(f"Registered the following router urls: {router.urls}")


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
        url(r"^admin/login/", AdminOIDCLogin.as_view()),
        url(r"^admin/", admin.site.urls),
        url(r"^admin/impersonate/", include("impersonate.urls")),
        url(
            r"^admin/allocations/",
            include("allocations.urls", namespace="allocations_admin"),
        ),
        # contrib urls
        url(r"^oidc/", include("mozilla_django_oidc.urls")),
        url(r"^ckeditor/", include("ckeditor_uploader.urls")),
        url(r"^terms/", include("termsandconditions.urls")),
        url(
            r"^sitemap\.xml$",
            sitemap,
            {"sitemaps": {"cmspages": CMSSitemap}},
            name="django.contrib.sitemaps.views.sitemap",
        ),
        # custom urls
        url(r"^login/", chameleon_os_login.custom_login, name="login"),
        url(r"^logout/", chameleon_os_login.custom_logout, name="logout"),
        url(r"^register/", chameleon_views.OIDCRegisterView.as_view(), name="register"),
        # Rollout endpoints for new login
        url(
            r"^auth/force-password-login/$",
            chameleon_views.force_password_login,
            name="force_password_login",
        ),
        url(
            r"^auth/confirm/$",
            chameleon_os_login.confirm_legacy_credentials,
            name="federation_confirm_legacy_credentials",
        ),
        url(
            r"^user/migrate/$",
            chameleon_views.migrate,
            name="federation_migrate_account",
        ),
        url(r"^api/user/migrate/status/$", chameleon_views.api_migration_state),
        url(r"^api/user/migrate/job/$", chameleon_views.api_migration_job),
        # Legacy account endpoints
        url(r"^user/", include("tas.urls", namespace="tas")),
        url(r"^password-reset/$", chameleon_views.password_reset),
        url(r"^user/dashboard/", chameleon_views.dashboard, name="dashboard"),
        url(
            r"^feed\.xml",
            RedirectView.as_view(permanent=True, url=reverse_lazy("user_news:feed")),
        ),
        url(r"^user/outages/$", OutageListView.as_view(), name="outage_list"),
        url(r"^user/outages/rss/$", OutageFeed(), name="outage_feed"),
        url(
            r"^user/outages/(?P<slug>[-_\w]+)/$",
            OutageDetailView.as_view(),
            name="outage_detail",
        ),
        url(r"^hardware/", include("g5k_discovery.urls", namespace="hardware")),
        # Unclear if this legacy route still needs to be supported
        url(
            r"^user/discovery/",
            RedirectView.as_view(
                permanent=True, url=reverse_lazy("hardware:discovery")
            ),
        ),
        url(r"^user/projects/", include("projects.urls", namespace="projects")),
        url(r"^user/help/", include("djangoRT.urls", namespace="djangoRT")),
        url(
            r"^user/early-user-program/",
            include("cc_early_user_support.urls", namespace="cc_early_user_support"),
        ),
        url(
            r"^user/webinar/",
            include("webinar_registration.urls", namespace="webinar_registration"),
        ),
        # mailing list resource for mailman autosubscribe
        url(
            r"^mailman/new_members.txt$",
            chameleon_mailman_views.mailman_export_list,
            name="mailman_export_list",
        ),
        # ensure default djangocms_blog namespace is registered at /blog
        # (the auto-setup hook doesn't work well if the page is moved in the hierarchy)
        url(r"^blog/", include("djangocms_blog.urls", namespace="Blog")),
        # robots.txt
        url(
            r"^robots.txt$",
            TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        ),
        # cms urls
        url(r"^taggit_autosuggest/", include("taggit_autosuggest.urls")),
        url(r"^", include("blog_comments.urls")),
        url(r"^", include("cms.urls")),
        # /appliances is bound to appliance_catalog app via CMS integration
        # /share is bound to sharing_portal app via CMS integration
        # /news is bound to user_news app via CMS integration
    ]
    #+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    #+ router.get_urls()
)

urlpatterns += router.urls
