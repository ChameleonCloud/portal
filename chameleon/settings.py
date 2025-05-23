"""
Django settings file. This gets most values by loading a .env file.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import re
import sys

from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

gettext = lambda s: s

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "NOT_A_SECRET")

# SECURITY WARNING: don't run with debug turned on in production!
# https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-DEBUG
DEBUG = os.environ.get("DJANGO_ENV", "debug").lower() == "debug"

# OpenStack Properties
OPENSTACK_UC_REGION = os.environ.get("OPENSTACK_UC_REGION", "CHI@UC")
OPENSTACK_TACC_REGION = os.environ.get("OPENSTACK_TACC_REGION", "CHI@TACC")
OPENSTACK_KVM_REGION = os.environ.get("OPENSTACK_KVM_REGION", "KVM@TACC")
OPENSTACK_SERVICE_USERNAME = os.environ.get("OPENSTACK_SERVICE_USERNAME", "")
OPENSTACK_SERVICE_PASSWORD = os.environ.get("OPENSTACK_SERVICE_PASSWORD", "")
OPENSTACK_SERVICE_PROJECT_ID = os.environ.get("OPENSTACK_SERVICE_PROJECT_ID", "")
OPENSTACK_SERVICE_PROJECT_NAME = os.environ.get(
    "OPENSTACK_SERVICE_PROJECT_NAME", "services"
)
OPENSTACK_UC_AUTH_URL = os.environ.get(
    "OPENSTACK_UC_AUTH_URL", "https://chi.uc.chameleoncloud.org:5000/v3"
)
OPENSTACK_TACC_AUTH_URL = os.environ.get(
    "OPENSTACK_TACC_AUTH_URL", "https://chi.tacc.chameleoncloud.org:5000/v3"
)
OPENSTACK_KVM_AUTH_URL = os.environ.get(
    "OPENSTACK_KVM_AUTH_URL", "https://kvm.tacc.chameleoncloud.org:5000/v3"
)
OPENSTACK_AUTH_REGIONS = {
    OPENSTACK_UC_REGION: OPENSTACK_UC_AUTH_URL,
    OPENSTACK_TACC_REGION: OPENSTACK_TACC_AUTH_URL,
    OPENSTACK_KVM_REGION: OPENSTACK_KVM_AUTH_URL,
}
TACC_OPENSTACK_DB_HOST = os.environ.get("TACC_OPENSTACK_DB_HOST")
TACC_OPENSTACK_DB_USER = os.environ.get("TACC_OPENSTACK_DB_USER")
TACC_OPENSTACK_DB_PASSWORD = os.environ.get("TACC_OPENSTACK_DB_PASSWORD")
UC_OPENSTACK_DB_HOST = os.environ.get("UC_OPENSTACK_DB_HOST")
UC_OPENSTACK_DB_USER = os.environ.get("UC_OPENSTACK_DB_USER")
UC_OPENSTACK_DB_PASSWORD = os.environ.get("UC_OPENSTACK_DB_PASSWORD")

REGION_OPENSTACK_DB_CONNECT = {}
if TACC_OPENSTACK_DB_HOST:
    REGION_OPENSTACK_DB_CONNECT[OPENSTACK_TACC_REGION] = {
        "host": TACC_OPENSTACK_DB_HOST,
        "user": TACC_OPENSTACK_DB_USER,
        "passwd": TACC_OPENSTACK_DB_PASSWORD,
    }
if UC_OPENSTACK_DB_HOST:
    REGION_OPENSTACK_DB_CONNECT[OPENSTACK_UC_REGION] = {
        "host": UC_OPENSTACK_DB_HOST,
        "user": UC_OPENSTACK_DB_USER,
        "passwd": UC_OPENSTACK_DB_PASSWORD,
    }

# Change to http for local dev only
SSO_CALLBACK_PROTOCOL = os.environ.get("SSO_CALLBACK_PROTOCOL", "https")
SSO_CALLBACK_VALID_HOSTS = os.environ.get("SSO_CALLBACK_VALID_HOSTS", [])

TACC_USER_PORTAL_HOST = "https://portal.tacc.utexas.edu"

# Sharing portal
ARTIFACT_SHARING_SWIFT_ENDPOINT = os.getenv("ARTIFACT_SHARING_SWIFT_ENDPOINT")
ARTIFACT_SHARING_SWIFT_TEMP_URL = os.getenv("ARTIFACT_SHARING_SWIFT_TEMP_URL")
ARTIFACT_SHARING_SWIFT_CONTAINER = os.getenv(
    "ARTIFACT_SHARING_SWIFT_CONTAINER", "trovi"
)
ARTIFACT_SHARING_JUPYTERHUB_URL = os.getenv(
    "ARTIFACT_SHARING_JUPYTERHUB_URL", "https://jupyter.chameleoncloud.org"
)
ZENODO_URL = os.getenv("ZENODO_URL", "https://zenodo.org")
ZENODO_DEFAULT_ACCESS_TOKEN = os.getenv("ZENODO_DEFAULT_ACCESS_TOKEN")
ARTIFACT_OWNER_PROVIDER = os.getenv("ARTIFACT_OWNER_PROVIDER", "chameleon")
ARTIFACT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M%Z"
TROVI_API_BASE_URL = os.getenv(
    "TROVI_API_BASE_URL", "https://trovi.chameleoncloud.org/"
)

# TEMPLATE_DEBUG = DEBUG

_default_allowed_hosts = [
    "127.0.0.1",
    "localhost",
    "chameleon.local",
    "chameleoncloud.org",
    "www.chameleoncloud.org",
    "dev.chameleoncloud.org",
    "www.dev.chameleoncloud.org",
    "129.114.97.96",
    "129.114.97.87",
]
ALLOWED_HOSTS = _default_allowed_hosts
# ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", default=_default_allowed_hosts)

# Application definition

INSTALLED_APPS = (
    ##
    # django-cms prereqs
    #
    "djangocms_admin_style",
    "djangocms_text_ckeditor",
    "blog_comments",
    ##
    # core apps
    #
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mozilla_django_oidc",
    ##
    # django-cms
    #
    "cms",
    "menus",
    "sekizai",
    "treebeard",
    "djangocms_style",
    "djangocms_column",
    "djangocms_file",
    "djangocms_link",
    "djangocms_picture",
    "djangocms_snippet",
    "djangocms_video",
    ##
    # contrib
    #
    "ckeditor",
    "pipeline",
    "django_recaptcha",
    "bootstrap3",
    "termsandconditions",
    "markdown_deux",
    "webpack_loader",
    "rest_framework",
    ##
    # custom
    #
    "balance_service",
    "chameleon",
    "chameleon_mailman",
    "chameleon_token",
    "util",
    "tas",
    "djangoRT",
    "projects",
    "user_news",
    "djng",
    "g5k_discovery",
    "allocations",
    "appliance_catalog",
    "sharing_portal",
    "webinar_registration",
    "chameleon_cms_integrations",
    # djangocms-blog
    "filer",
    "easy_thumbnails",
    "aldryn_apphooks_config",
    "parler",
    "taggit",
    "taggit_autosuggest",
    "meta",
    "sortedm2m",
    "djangocms_blog",
    "djangocms_icon",
    "djangocms_bootstrap4",
    "djangocms_bootstrap4.contrib.bootstrap4_alerts",
    "djangocms_bootstrap4.contrib.bootstrap4_badge",
    "djangocms_bootstrap4.contrib.bootstrap4_card",
    "djangocms_bootstrap4.contrib.bootstrap4_carousel",
    "djangocms_bootstrap4.contrib.bootstrap4_collapse",
    "djangocms_bootstrap4.contrib.bootstrap4_content",
    "djangocms_bootstrap4.contrib.bootstrap4_grid",
    "djangocms_bootstrap4.contrib.bootstrap4_jumbotron",
    "djangocms_bootstrap4.contrib.bootstrap4_listgroup",
    "djangocms_bootstrap4.contrib.bootstrap4_media",
    "djangocms_bootstrap4.contrib.bootstrap4_tabs",
    "djangocms_bootstrap4.contrib.bootstrap4_utilities",
)

MIDDLEWARE = (
    "djng.middleware.AngularUrlMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "termsandconditions.middleware.TermsAndConditionsRedirectMiddleware",
    "user_news.middleware.UserNewsNotificationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "cms.middleware.utils.ApphookReloadMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
    "mozilla_django_oidc.middleware.RefreshOIDCAccessToken",
)

ROOT_URLCONF = "chameleon.urls"

WSGI_APPLICATION = "chameleon.wsgi.application"

MARKDOWN_DEUX_STYLES = {
    "default": {
        "extras": {
            "code-friendly": None,
        },
        "safe_mode": False,
    },
    "blog_comments": {
        "extras": {
            "code-friendly": None,
        },
        "safe_mode": "escape",
    },
}

TESTING = "test" in sys.argv or "test_coverage" in sys.argv

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

if not TESTING and os.environ.get("DB_NAME"):
    # mysql connection
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME"),
            "HOST": os.environ.get("DB_HOST"),
            "PORT": os.environ.get("DB_PORT"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "TEST": {
                "NAME": os.environ.get("DB_NAME") + "_test",
            },
        },
    }
else:
    # use SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "US/Central"

USE_TZ = True

SITE_ID = 1

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = "/static"
STATIC_URL = "/static/"

MEDIA_ROOT = "/media"
MEDIA_URL = "/media/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "pipeline.finders.PipelineFinder",
)

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    # if not set explicitly, make admin only
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAdminUser",
    ],
    # if not set explicitly, return json response.
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
}

# Keycloak OIDC Authentication
OIDC_RP_CLIENT_ID = os.environ.get("OIDC_RP_CLIENT_ID")
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET")
OIDC_RP_SIGN_ALGO = os.environ.get("OIDC_RP_SIGN_ALGO")
OIDC_OP_JWKS_ENDPOINT = os.environ.get("OIDC_OP_JWKS_ENDPOINT")
OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get("OIDC_OP_AUTHORIZATION_ENDPOINT")
OIDC_OP_REGISTRATION_ENDPOINT = os.environ.get("OIDC_OP_REGISTRATION_ENDPOINT")
OIDC_OP_TOKEN_ENDPOINT = os.environ.get("OIDC_OP_TOKEN_ENDPOINT")
OIDC_OP_USER_ENDPOINT = os.environ.get("OIDC_OP_USER_ENDPOINT")
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_REFRESH_TOKEN = True
# This should match the Access Token Validity for the realm (or override for the portal client in Keycloak)
OIDC_RENEW_TOKEN_EXPIRY_SECONDS = 60 * 5
OIDC_EXEMPT_URLS = ["logout"]
LOGOUT_REDIRECT_URL = os.environ.get("LOGOUT_REDIRECT_URL")
# This should match the value of SSO Session Idle for the portal client in Keycloak
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7

# Keycloak Client
KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL")
KEYCLOAK_REALM_NAME = os.environ.get("KEYCLOAK_REALM_NAME", "chameleon")
KEYCLOAK_PORTAL_ADMIN_CLIENT_ID = os.environ.get("KEYCLOAK_PORTAL_ADMIN_CLIENT_ID")
KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET = os.environ.get(
    "KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET"
)
KEYCLOAK_CLIENT_PROVIDER_ALIAS = os.environ.get("KEYCLOAK_CLIENT_PROVIDER_ALIAS")
KEYCLOAK_CLIENT_PROVIDER_SUB = os.environ.get("KEYCLOAK_CLIENT_PROVIDER_SUB")

AUTHENTICATION_BACKENDS = ("chameleon.ChameleonOIDCAuthBackend.ChameleonOIDCAB",)

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/user/dashboard"


# Recaptcha keys
RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY", default="")
RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY", default="")


OPENID_PROVIDERS = {
    "geni": {
        "name": "GENI",
        "site_url": "http://www.geni.net/",
        "openid_url": "https://portal.geni.net/server/server.php",
    },
}


#####
#
# Logger config
#
#####
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOG_VERBOSITY = os.environ.get("DJANGO_LOG_VERBOSITY", "SHORT")
SQL_LEVEL = os.environ.get("DJANGO_SQL_LEVEL", "INFO")
SQL_VERBOSITY = os.environ.get("DJANGO_SQL_VERBOSITY", "SHORT")
CONSOLE_WIDTH = os.environ.get("DJANGO_LOG_WIDTH", 100)
CONSOLE_INDENT = os.environ.get("DJANGO_LOG_INDENT", 2)

import logging

# Ensure Python `warnings` are ingested by logging infra
logging.captureWarnings(True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "default_short": {
            "format": "[DJANGO] %(levelname)s %(name)s.%(funcName)s: %(message)s"
        },
        "default_verbose": {
            "format": "[DJANGO] %(levelname)s %(asctime)s %(module)s %(name)s.%(funcName)s: %(message)s"
        },
        "sql_short": {
            "format": "[DJANGO-SQL] [%(duration).3f] %(sql)s",
        },
        "sql_verbose": {
            "()": "util.sql_format.SQLFormatter",
            "format": "[DJANGO-SQL] [%(duration).3f] %(statement)s",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": f"default_{LOG_VERBOSITY.lower()}",
        },
        "console-sql": {
            "filters": ["require_debug_true"],
            "level": SQL_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": f"sql_{SQL_VERBOSITY.lower()}",
        },
    },
    "loggers": {
        "default": {"handlers": ["console"], "level": "DEBUG"},
        "console": {"handlers": ["console"], "level": "DEBUG"},
        "django": {"handlers": ["console"], "level": "INFO"},
        "py.warnings": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["console-sql"],
            "level": "DEBUG",
            "propagate": False,
        },
        "pipeline": {"handlers": ["console"], "level": "INFO"},
        "pytas": {"handlers": ["console"], "level": "INFO"},
        "chameleon_cms_integrations": {"handlers": ["console"], "level": "INFO"},
        "openid": {"handlers": ["console"], "level": "INFO"},
        "chameleon": {"handlers": ["console"], "level": "INFO"},
        "auth": {"handlers": ["console"], "level": "INFO"},
        "tas": {"handlers": ["console"], "level": "INFO"},
        "projects": {"handlers": ["console"], "level": "INFO"},
        "sharing_portal": {"handlers": ["console"], "level": "INFO"},
        "allocations": {"handlers": ["console"], "level": "INFO"},
        "chameleon_mailman": {"handlers": ["console"], "level": "INFO"},
        "util": {"handlers": ["console"], "level": "INFO"},
        "balance_service": {"handlers": ["console"], "level": "INFO"},
    },
}


#####
#
# CMS Config
#
#####
CMS_TOOLBAR_URL__EDIT_ON = (
    "tk5VAFwlx9IKSoczFi3XlNv4xbGeNn8pzAlCu9555gi2238lu36PAj8jQgtch3U"
)

CMS_TEMPLATES = (
    # Customize this
    ("cms_page.html", "Default Page"),
    ("cms_custom_page.html", "Advanced Page"),
)

CMS_PERMISSION = True

CMS_PLACEHOLDER_CONF = {}

DJANGOCMS_STYLE_CHOICES = ["enable-toc", "sidebar-toc", "header-toc"]

LANGUAGES = [
    ("en", "English"),
]

MIGRATION_MODULES = {
    "djangocms_text_ckeditor": "djangocms_text_ckeditor.migrations",
    "djangocms_column": "djangocms_column.migrations",
    "djangocms_flash": "djangocms_flash.migrations",
    "djangocms_inherit": "djangocms_inherit.migrations",
    "djangocms_style": "djangocms_style.migrations",
    "djangocms_file": "djangocms_file.migrations",
    "djangocms_link": "djangocms_link.migrations",
    "djangocms_picture": "djangocms_picture.migrations",
    "djangocms_teaser": "djangocms_teaser.migrations",
    "djangocms_video": "djangocms_video.migrations",
}

#####
#
# Project Extras/Nickname API token for json endpoint
#
#####
PROJECT_EXTRAS_API_TOKEN = os.environ.get("PROJECT_EXTRAS_API_TOKEN", None)
DAYPASS_LIMIT = 10

#####
#
# CKEditor Config
#
#####
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Chameleon",
        "toolbar_Chameleon": [
            [
                "Styles",
                "Format",
                "Bold",
                "Italic",
                "Underline",
                "Strike",
                "SpellChecker",
                "Undo",
                "Redo",
            ],
            ["Link", "Unlink", "Anchor"],
            ["Image", "Table", "HorizontalRule"],
            ["BulletedList", "NumberedList"],
            ["Source"],
        ],
    },
}

#####
#
# Additional config to allow iframes
#
#####
TEXT_ADDITIONAL_TAGS = "iframe"
TEXT_ADDITIONAL_ATTRIBUTES = (
    "scrolling",
    "allowfullscreen",
    "frameborder",
    "src",
    "height",
    "width",
)

#####
#
# Pipeline config
#
#####
PIPELINE = {
    "COMPILERS": ("pipeline.compilers.sass.SASSCompiler",),
    "SASS_ARGUMENTS": "--compass --style compressed",
    "CSS_COMPRESSOR": "pipeline.compressors.yuglify.YuglifyCompressor",
    "JS_COMPRESSOR": "pipeline.compressors.uglifyjs.UglifyJSCompressor",
    "STYLESHEETS": {
        "main": {
            "source_filenames": (
                "styles/main.scss",
                "styles/corner-ribbon.css",
                "djangoRT/css/djangoRT.css",
                "projects/css/projects.scss",
            ),
            "output_filename": "styles/main.css",
        },
        "embed": {
            "source_filenames": ("styles/embed.scss",),
            "output_filename": "styles/embed.css",
        },
        "appliance_catalog": {
            "source_filenames": (
                "appliance_catalog/css/appliance_catalog.css",
                "appliance_catalog/vendor/angular/angular-csp.css",
                "appliance_catalog/vendor/angular-bootstrap-toggle-switch/style/bootstrap3/angular-toggle-switch-bootstrap-3.css",
            ),
            "output_filename": "styles/appliance_catalog.css",
        },
    },
    "JAVASCRIPT": {
        "all": {
            "source_filenames": (
                "bower_components/jquery/dist/jquery.js",
                "bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js",
                "bower_components/toc/dist/toc.js",
                "scripts/auto-table-of-contents.js",
                "djangoRT/js/djangoRT.js",
            ),
            "output_filename": "scripts/all.js",
        },
        "embed": {
            "source_filenames": (
                "bower_components/jquery/dist/jquery.js",
                "bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js",
            ),
            "output_filename": "scripts/embed.js",
        },
    },
}

# compress when collect static
STATICFILES_STORAGE = "pipeline.storage.PipelineStorage"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [
            os.path.join(BASE_DIR, "chameleon", "templates"),
        ],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.csrf",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "chameleon.context_processors.google_analytics",
                "sekizai.context_processors.sekizai",
                "cms.context_processors.cms_settings",
            ],
            # https://docs.djangoproject.com/en/1.11/topics/templates/#module-django.template.backends.django
            "debug": os.environ.get("DJANGO_ENV", "DEBUG") == "DEBUG",
        },
    },
]

WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": not DEBUG,
        "BUNDLE_DIR_NAME": "vue/",  # must end with slash
        "STATS_FILE": os.path.join(BASE_DIR, "webpack-stats.json"),
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
    }
}

#####
#
# Google Analytics
#
#####
GOOGLE_ANALYTICS_PROPERTY_ID = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID")


#####
#
# Django RT
#
#####
DJANGO_RT = {
    "RT_HOST": os.environ.get("RT_HOST"),
    "RT_UN": os.environ.get("RT_USERNAME"),
    "RT_PW": os.environ.get("RT_PASSWORD"),
    "RT_QUEUE": os.environ.get("RT_DEFAULT_QUEUE"),
}


#####
#
# Bootstrap3 Settings
#
#####
BOOTSTRAP3 = {
    "required_css_class": "required",
    "field_renderers": {
        "default": "util.forms.renderers.ChameleonFieldRenderer",
    },
}


#####
#
# Terms and Conditions settings
#
#####
DEFAULT_TERMS_SLUG = "site-terms"
ACCEPT_TERMS_PATH = "/terms/accept/"
TERMS_EXCLUDE_URL_PREFIX_LIST = {"/admin", "/terms"}
TERMS_EXCLUDE_URL_LIST = {"/", "/termsrequired/", "/logout/", "/securetoo/"}
MULTIPLE_ACTIVE_TERMS = True  # Multiple kinds of T&Cs active at once (like site-terms, and contributor-terms).


#####
#
# Grid'5000 API
#
#####
G5K_API_ROOT = "http://referenceapi:8000"

#####
#
# Edge HW Discovery API
#
#####
EDGE_HW_ROOT = "http://edgehwdiscovery:5000"

#####
#
# Email Configuration
#
#####
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_USE_TLS = EMAIL_PORT == 587
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@chameleoncloud.org")


# User News Outage Notification
OUTAGE_NOTIFICATION_EMAIL = os.environ.get("OUTAGE_NOTIFICATION_EMAIL", "")


#####
#
# GENI Federation
#
#####
GENI_FEDERATION_PROJECTS = {
    "geni": {
        "id": "97762ef8-86ea-4212-b41a-ac5d75467c16",
        "name": "Chameleon-Federation",
        "url": "https://portal.geni.net/secure/join-this-project.php?project_id=97762ef8-86ea-4212-b41a-ac5d75467c16",
    },
    "chameleon": {
        "id": "26427",
        "name": "GENI-Federation",
        "url": "https://www.chameleoncloud.org/user/projects/26427/",
        "charge_code": "CH-817201",
    },
}


###
# Opbeat Integration
#
# if os.environ.get('OPBEAT_ORGANIZATION_ID'):
#     INSTALLED_APPS += ('opbeat.contrib.django',)
#     OPBEAT = {
#         'ORGANIZATION_ID': os.environ.get('OPBEAT_ORGANIZATION_ID', ''),
#         'APP_ID': os.environ.get('OPBEAT_APP_ID', ''),
#         'SECRET_TOKEN': os.environ.get('OPBEAT_SECRET_TOKEN', ''),
#     }
#     # Opbeat middleware needs to be first
#     MIDDLEWARE_CLASSES = (
#         'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
#         ) + MIDDLEWARE_CLASSES

THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    "filer.thumbnail_processors.scale_and_crop_with_subject_location",
    "easy_thumbnails.processors.filters",
)
META_SITE_PROTOCOL = "http"
META_USE_SITES = True
BLOG_MULTISITE = False

PARLER_LANGUAGES = {
    1: (
        {
            "code": "en",
        },
    ),
    "default": {
        "fallbacks": ["en"],
    },
}

# overwrite default django params
# ref: https://github.com/divio/django-filer/issues/1031
FILE_UPLOAD_MAX_MEMORY_SIZE = 10000000
FILE_UPLOAD_PERMISSIONS = 0o644

# ALLOCATIONS
ALLOCATIONS_BALANCE_SERVICE_ROOT_URL = os.environ.get(
    "ALLOCATIONS_BALANCE_SERVICE_ROOT_URL", ""
)
PROJECT_ALLOCATION_DETAILS_TOKEN = os.environ.get(
    "PROJECT_ALLOCATION_DETAILS_TOKEN", None
)

# check if balance URL starts with https://www.chameleoncloud.org and https://chameleoncloud.org.
# if it matches, raise an exception to prevent testing against production redis db.
# in prod it uses a local container host configuration value.
if re.match("^https://.*chameleoncloud.org*", ALLOCATIONS_BALANCE_SERVICE_ROOT_URL):
    raise ValueError(
        "Please use local container host configuration to access production redis!"
    )

PENDING_ALLOCATION_NOTIFICATION_EMAIL = os.environ.get(
    "PENDING_ALLOCATION_NOTIFICATION_EMAIL", ""
)
ACTIVATE_EXPIRE_ALLOCATION_FREQUENCY = 60 * 5
ACTIVATE_EXPIRE_INVITATION_FREQUENCY = 60 * 5

########
# Tasks
########

# Outage email notifications
OUTAGE_EMAIL_REMINDER_TIMEDELTA = 60 * 60 * 2
OUTAGE_REMINDER_FREQUENCY = 60 * 10

CELERY_BROKER_URL = "redis://redis:6379"
CELERY_RESULT_BACKEND = "redis://redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"
CELERY_BEAT_SCHEDULE = {
    "send-outage-reminders": {
        "task": "chameleon_mailman.tasks.send_outage_reminders",
        "schedule": crontab(minute="*/{}".format(int(OUTAGE_REMINDER_FREQUENCY // 60))),
        "args": (OUTAGE_REMINDER_FREQUENCY, OUTAGE_EMAIL_REMINDER_TIMEDELTA),
    },
    "activate-expire-allocations": {
        "task": "allocations.tasks.activate_expire_allocations",
        "schedule": crontab(
            minute="*/{}".format(int(ACTIVATE_EXPIRE_ALLOCATION_FREQUENCY // 60))
        ),
    },
    "activate-expire-invitations": {
        "task": "projects.tasks.activate_expire_invitations",
        "schedule": crontab(
            minute="*/{}".format(int(ACTIVATE_EXPIRE_INVITATION_FREQUENCY // 60))
        ),
    },
    "end_daypasses": {
        "task": "projects.tasks.end_daypasses",
        "schedule": crontab(minute="*/5"),
    },
    "warn-user-for-expiring-allocation": {
        "task": "allocations.tasks.warn_user_for_expiring_allocation",
        "schedule": crontab(minute=0, hour=7),
    },
    "warn-user-for-low-allocation": {
        "task": "allocations.tasks.warn_user_for_low_allocations",
        "schedule": crontab(minute=30, hour=7),
    },
}
if DEBUG:
    CELERY_BEAT_SCHEDULE = {}

# Djangocms_blog templates
BLOG_PLUGIN_TEMPLATE_FOLDERS = (
    ("frontpage", _("Frontpage Display")),  # reads templates/djangocms_blog/frontpage/
)

# Content-Security-Policy
# Ensure that all items include self.
CSP_FRAME_ANCESTORS = "'self'"  # Similar to X-Frame-Options: SAMEORIGIN
CSP_SCRIPT_SRC = [
    "'self'",
    "https://www.googletagmanager.com",
    "https://www.google-analytics.com",
    "https://www.google.com/recaptcha/",
    "https://www.gstatic.com/recaptcha/",
    "https://cdnjs.cloudflare.com/ajax/libs/ace/1.9.6/ace.js",  # snippet editor
    "'unsafe-inline'",
]
CSP_CONNECT_SRC = [
    "'self'",
    "https://www.google-analytics.com",
]
CSP_FRAME_SRC = [
    "'self'",
    "https://www.google.com/recaptcha/",
    "https://recaptcha.google.com/recaptcha/",
]
CSP_IMG_SRC = [
    "'self'",
    "https://chameleoncloud.org",
    "https://www.chameleoncloud.org",
    "https://www.google-analytics.com",
    "https://*.googleusercontent.com",
]
CSP_FONT_SRC = [
    "'self'",
    "https://fonts.gstatic.com",
]
CSP_STYLE_SRC = [
    "'self'",
    "https://fonts.googleapis.com",
    "'unsafe-inline'",
]
CSP_INCLUDE_NONCE_IN = ["script-src"]
# Add rules for the Vue JS dev server
if DEBUG:
    vue_dev_server = "http://localhost:9000/"
    CSP_SCRIPT_SRC.append(vue_dev_server)
    CSP_IMG_SRC.append(vue_dev_server)
    CSP_STYLE_SRC.append(vue_dev_server)
    CSP_CONNECT_SRC = ["'self'", vue_dev_server]
    # Webpack uses eval to provide its Hot Module Replacement capability
    CSP_SCRIPT_SRC.append("'unsafe-eval'")

CACHES = {
    "default": {
        "BACKEND": os.environ.get(
            "CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": os.environ.get("CACHE_LOCATION", "LOC_MEM_CACHE"),
    }
}

if DEBUG:
    SILENCED_SYSTEM_CHECKS = ["captcha.recaptcha_test_key_error"]


########
# Balance Service
########
ALLOWED_OPENSTACK_SERVICE_USERS = os.environ.get(
    "ALLOWED_OPENSTACK_SERVICE_USERS", ["blazar", "portal", "smoke-tests"]
)

########
# Publication
########
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
SCOPUS_API_KEY = os.environ.get("SCOPUS_API_KEY")
SCOPUS_INSTITUTION_KEY = os.environ.get("SCOPUS_INSTITUTION_KEY")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]
