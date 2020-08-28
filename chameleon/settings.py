"""
Django settings for chameleon project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
from __future__ import absolute_import

import os
import django
from celery.schedules import crontab
from django.utils.translation import ugettext_lazy as _

gettext = lambda s: s

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'NOT_A_SECRET')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_ENV', 'DEBUG') == 'DEBUG'

## OpenStack Properties
OPENSTACK_KEYSTONE_URL = os.environ.get('OPENSTACK_KEYSTONE_URL', 'https://chi.tacc.chameleoncloud.org:5000/v3')
OPENSTACK_ALT_KEYSTONE_URL = os.environ.get('OPENSTACK_ALT_KEYSTONE_URL', 'https://chi.uc.chameleoncloud.org:5000/v3')
OS_PROJECT_DOMAIN_NAME = os.environ.get('OS_PROJECT_DOMAIN_NAME', 'Default')
OPENSTACK_UC_REGION = os.environ.get('OPENSTACK_UC_REGION', 'CHI@UC')
OPENSTACK_TACC_REGION = os.environ.get('OPENSTACK_TACC_REGION', 'CHI@TACC')
OPENSTACK_SERVICE_USERNAME = os.environ.get('OPENSTACK_SERVICE_USERNAME', '')
OPENSTACK_SERVICE_PASSWORD = os.environ.get('OPENSTACK_SERVICE_PASSWORD', '')
OPENSTACK_SERVICE_PROJECT_ID = os.environ.get('OPENSTACK_SERVICE_PROJECT_ID', '')
OPENSTACK_SERVICE_PROJECT_NAME = os.environ.get('OPENSTACK_SERVICE_PROJECT_NAME', 'services')
OPENSTACK_AUTH_REGIONS = {
    OPENSTACK_UC_REGION:   os.environ.get('OPENSTACK_UC_AUTH_URL', 'https://chi.uc.chameleoncloud.org:5000/v3'),
    OPENSTACK_TACC_REGION: os.environ.get('OPENSTACK_TACC_AUTH_URL', 'https://chi.tacc.chameleoncloud.org:5000/v3'),
}
## Change to http for local dev only
SSO_CALLBACK_PROTOCOL = os.environ.get('SSO_CALLBACK_PROTOCOL', 'https')
SSO_CALLBACK_VALID_HOSTS = os.environ.get('SSO_CALLBACK_VALID_HOSTS', [])

# Sharing portal
SHARING_PORTAL_JUPYTERHUB_URL = os.environ.get('SHARING_PORTAL_JUPYTERHUB_URL', 'https://jupyter.chameleoncloud.org')
SHARING_PORTAL_ZENODO_SANDBOX = os.environ.get('SHARING_PORTAL_ZENODO_SANDBOX') is not None

#TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'chameleon.local',
    'chameleoncloud.org',
    'www.chameleoncloud.org',
    'www.tacc.chameleoncloud.org',
    'www.chameleon.tacc.utexas.edu',
    'dev.chameleon.tacc.utexas.edu',
    'local.chameleoncloud.org',
]

# Application definition

INSTALLED_APPS = (
    ##
    # django-cms prereqs
    #
    'djangocms_admin_style',
    'djangocms_text_ckeditor',
    'blog_comments',

    ##
    # core apps
    #
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mozilla_django_oidc',

    ##
    # django-cms
    #
    'cms',
    'menus',
    'sekizai',
    'treebeard',
    'djangocms_style',
    'djangocms_column',
    'djangocms_file',
    'djangocms_flash',
    'djangocms_inherit',
    'djangocms_link',
    'djangocms_picture',
    'djangocms_teaser',
    'djangocms_video',
    'reversion',

    ##
    # contrib
    #
    'ckeditor',
    'pipeline',
    'captcha',
    'bootstrap3',
    'termsandconditions',
    'impersonate',
    'markdown_deux',

    ##
    # custom
    #
    'chameleon',
    'chameleon_openid',
    'chameleon_mailman',
    'chameleon_token',
    'usage',
    'util',
    'tas',
    'djangoRT',
    'projects',
    'user_news',
    'djng',
    'g5k_discovery',
    'cc_early_user_support',
    'allocations',
    'appliance_catalog',
    'sharing_portal',
    'webinar_registration',
    'chameleon_cms_integrations',

    # djangocms-blog

    'filer',
    'easy_thumbnails',
    'aldryn_apphooks_config',
    'parler',
    'taggit',
    'taggit_autosuggest',
    'meta',
    'sortedm2m',
    'djangocms_blog',
)

MIDDLEWARE_CLASSES = (
    'djng.middleware.AngularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'termsandconditions.middleware.TermsAndConditionsRedirectMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'user_news.middleware.UserNewsNotificationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.utils.ApphookReloadMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
)

ROOT_URLCONF = 'chameleon.urls'

WSGI_APPLICATION = 'chameleon.wsgi.application'

MARKDOWN_DEUX_STYLES = {
                           "default":{
                              "extras":{
                                 "code-friendly":None,

                              },
                              "safe_mode":False,

                           },
                           "blog_comments":{
                              "extras":{
                                 "code-friendly":None,

                              },
                              "safe_mode":"escape",

                           },

                        }

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

if os.environ.get('DB_NAME'):
    # mysql connection
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
        },
    }
else:
    # use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        },
    }

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en'

TIME_ZONE = 'US/Central'

USE_TZ = True

SITE_ID = 1

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_ROOT = '/var/www/chameleoncloud.org/static/'
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    '/var/www/static/',
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

'''
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR,'chameleon','templates'),
)
'''
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

## Keycloak OIDC Authentication
OIDC_RP_CLIENT_ID = os.environ.get('OIDC_RP_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = os.environ.get('OIDC_RP_CLIENT_SECRET')
OIDC_RP_SIGN_ALGO = os.environ.get('OIDC_RP_SIGN_ALGO')
OIDC_OP_JWKS_ENDPOINT = os.environ.get('OIDC_OP_JWKS_ENDPOINT')
OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get('OIDC_OP_AUTHORIZATION_ENDPOINT')
OIDC_OP_TOKEN_ENDPOINT = os.environ.get('OIDC_OP_TOKEN_ENDPOINT')
OIDC_OP_USER_ENDPOINT = os.environ.get('OIDC_OP_USER_ENDPOINT')
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True

## Keycloak Client
KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL')
KEYCLOAK_REALM_NAME = os.environ.get('KEYCLOAK_REALM_NAME', 'chameleon')
KEYCLOAK_PORTAL_ADMIN_CLIENT_ID = os.environ.get('KEYCLOAK_PORTAL_ADMIN_CLIENT_ID')
KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET = os.environ.get('KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET')

AUTHENTICATION_BACKENDS = (
    'tas.auth.TASBackend',
    'chameleon_openid.backend.OpenIDBackend',
    'chameleon.ChameleonOIDCAuthBackend.ChameleonOIDCAB',
)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/user/dashboard'


OPENID_PROVIDERS = {
    'geni': {
        'name': 'GENI',
        'site_url': 'http://www.geni.net/',
        'openid_url': 'https://portal.geni.net/server/server.php'
    },
}


#####
#
# Logger config
#
#####
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[DJANGO] %(levelname)s %(asctime)s %(module)s %(name)s.%(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'default': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'console': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'pipeline': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'pytas': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'chameleon_cms_integrations': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'chameleon_openid': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'openid': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'chameleon': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'tas': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'projects': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'sharing_portal': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'allocations': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'chameleon_mailman': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'util': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}


#####
#
# CMS Config
#
#####
CMS_TOOLBAR_URL__EDIT_ON = 'tk5VAFwlx9IKSoczFi3XlNv4xbGeNn8pzAlCu9555gi2238lu36PAj8jQgtch3U'

CMS_TEMPLATES = (
    ## Customize this
    ('cms_page.html', 'Default Page'),
    ('cms_custom_page.html', 'Advanced Page'),
)

CMS_PERMISSION = True

CMS_PLACEHOLDER_CONF = {}

DJANGOCMS_STYLE_CHOICES = ['enable-toc', 'sidebar-toc', 'header-toc']

LANGUAGES = [
    ('en', 'English'),
]

MIGRATION_MODULES = {
    'djangocms_text_ckeditor': 'djangocms_text_ckeditor.migrations',
    'djangocms_column': 'djangocms_column.migrations',
    'djangocms_flash': 'djangocms_flash.migrations',
    'djangocms_inherit': 'djangocms_inherit.migrations',
    'djangocms_style': 'djangocms_style.migrations',
    'djangocms_file': 'djangocms_file.migrations',
    'djangocms_link': 'djangocms_link.migrations',
    'djangocms_picture': 'djangocms_picture.migrations',
    'djangocms_teaser': 'djangocms_teaser.migrations',
    'djangocms_video': 'djangocms_video.migrations',
}

#####
#
# Project Extras/Nickname API token for json endpoint
#
#####
PROJECT_EXTRAS_API_TOKEN = os.environ.get('PROJECT_EXTRAS_API_TOKEN', None)

#####
#
# CKEditor Config
#
#####
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Chameleon',
        'toolbar_Chameleon': [
            ['Styles', 'Format', 'Bold', 'Italic', 'Underline', 'Strike', 'SpellChecker', 'Undo', 'Redo'],
            ['Link', 'Unlink', 'Anchor'],
            ['Image', 'Table', 'HorizontalRule'],
            ['BulletedList', 'NumberedList'], ['Source'],
        ],
    },

}

#####
#
# Additional config to allow iframes
#
#####
TEXT_ADDITIONAL_TAGS = ('iframe')
TEXT_ADDITIONAL_ATTRIBUTES = ('scrolling', 'allowfullscreen','frameborder','src','height','width')

#####
#
# Pipeline config
#
#####
PIPELINE = {
    'COMPILERS': (
        'pipeline.compilers.sass.SASSCompiler',
    ),
    'SASS_ARGUMENTS': '--compass --style compressed',
    'CSS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'JS_COMPRESSOR': 'pipeline.compressors.slimit.SlimItCompressor',
    'STYLESHEETS': {
        'main': {
            'source_filenames': (
                'styles/main.scss',
                'styles/corner-ribbon.css',
                'djangoRT/css/djangoRT.css',
                'projects/css/projects.scss',
            ),
            'output_filename': 'styles/main.css',
        },
        'embed': {
            'source_filenames': (
                'styles/embed.scss',
            ),
            'output_filename': 'styles/embed.css',
        },
        'appliance_catalog': {
            'source_filenames': (
                'appliance_catalog/css/appliance_catalog.css',
                'appliance_catalog/vendor/angular/angular-csp.css',
                'appliance_catalog/vendor/angular-bootstrap-toggle-switch/style/bootstrap3/angular-toggle-switch-bootstrap-3.css',
            ),
            'output_filename': 'styles/appliance_catalog.css',
        }
    },
    'JAVASCRIPT': {
        'all': {
            'source_filenames': (
                'bower_components/jquery/dist/jquery.js',
                'bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js',
                'bower_components/toc/dist/toc.js',
                'scripts/auto-table-of-contents.js',
                'djangoRT/js/djangoRT.js',
            ),
            'output_filename': 'scripts/all.js',
        },
        'embed': {
            'source_filenames': (
                'bower_components/jquery/dist/jquery.js',
                'bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js',
            ),
            'output_filename': 'scripts/embed.js',
        }
    },
}

# compress when collect static
STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

TEMPLATES = [
{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': [os.path.join(BASE_DIR,'chameleon','templates'),],
    'OPTIONS': {
        'context_processors':
            [
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.debug',
            'django.template.context_processors.i18n',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
            'django.template.context_processors.csrf',
            'django.template.context_processors.request',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.request',
            'chameleon.context_processors.google_analytics',
            'sekizai.context_processors.sekizai',
            'cms.context_processors.cms_settings',
            ],
	'debug': os.environ.get('DJANGO_ENV', 'DEBUG') == 'DEBUG',
    }
},
]



#####
#
# Google Analytics
#
#####
GOOGLE_ANALYTICS_PROPERTY_ID = os.environ.get( 'GOOGLE_ANALYTICS_PROPERTY_ID' )


#####
#
# Django RT
#
#####
DJANGO_RT = {
    'RT_HOST': os.environ.get('RT_HOST'),
    'RT_UN': os.environ.get('RT_USERNAME'),
    'RT_PW': os.environ.get('RT_PASSWORD'),
    'RT_QUEUE': os.environ.get('RT_DEFAULT_QUEUE'),
}


#####
#
# Bootstrap3 Settings
#
#####
BOOTSTRAP3 = {
    'required_css_class': 'required',

     'field_renderers': {
        'default': 'util.forms.renderers.ChameleonFieldRenderer',
     }
}


#####
#
# Terms and Conditions settings
#
#####
DEFAULT_TERMS_SLUG = 'site-terms'
ACCEPT_TERMS_PATH = '/terms/accept/'
TERMS_EXCLUDE_URL_PREFIX_LIST = {'/admin', '/terms'}
TERMS_EXCLUDE_URL_LIST = {'/', '/termsrequired/', '/logout/', '/securetoo/'}
MULTIPLE_ACTIVE_TERMS = True # Multiple kinds of T&Cs active at once (like site-terms, and contributor-terms).


#####
#
# Grid'5000 API
#
#####
G5K_API_ROOT = 'http://referenceapi:8000'


#####
#
# Django Impersonate
#
#####
IMPERSONATE_REQUIRE_SUPERUSER = True


#####
#
# Email Configuration
#
#####
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('SMTP_HOST', 'localhost')
EMAIL_PORT = os.environ.get('SMTP_PORT', 25)
EMAIL_HOST_USER = os.environ.get('SMTP_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@chameleoncloud.org')

# User News Outage Notification
OUTAGE_NOTIFICATION_EMAIL = os.environ.get('OUTAGE_NOTIFICATION_EMAIL', '')


#####
#
# GENI Federation
#
#####
GENI_FEDERATION_PROJECTS = {
    'geni': {
        'id': '97762ef8-86ea-4212-b41a-ac5d75467c16',
        'name': 'Chameleon-Federation',
        'url': 'https://portal.geni.net/secure/join-this-project.php?project_id=97762ef8-86ea-4212-b41a-ac5d75467c16'
    },
    'chameleon': {
        'id': '26427',
        'name': 'GENI-Federation',
        'url': 'https://www.chameleoncloud.org/user/projects/26427/',
        'charge_code': 'CH-817201',
    },
}


###
# Opbeat Integration
#
if os.environ.get('OPBEAT_ORGANIZATION_ID'):
    INSTALLED_APPS += ('opbeat.contrib.django',)
    OPBEAT = {
        'ORGANIZATION_ID': os.environ.get('OPBEAT_ORGANIZATION_ID', ''),
        'APP_ID': os.environ.get('OPBEAT_APP_ID', ''),
        'SECRET_TOKEN': os.environ.get('OPBEAT_SECRET_TOKEN', ''),
    }
    # Opbeat middleware needs to be first
    MIDDLEWARE_CLASSES = (
        'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
        ) + MIDDLEWARE_CLASSES

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)
META_SITE_PROTOCOL = 'http'
META_USE_SITES = True
BLOG_MULTISITE = False

PARLER_LANGUAGES = {
    1: (
        {'code': 'en',},
    ),
    'default': {
        'fallbacks': ['en'],
    }
}

### overwrite default django params
# ref: https://github.com/divio/django-filer/issues/1031
FILE_UPLOAD_MAX_MEMORY_SIZE = 10000000
FILE_UPLOAD_PERMISSIONS = 0o644

# OUTAGE EMAIL REMINDER

CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
OUTAGE_EMAIL_REMINDER_TIMEDELTA = (60 * 60 * 2)
OUTAGE_REMINDER_FREQUENCY = (60 * 10)

# ALLOCATIONS
ALLOCATIONS_BALANCE_SERVICE_ROOT_URL = os.environ.get('ALLOCATIONS_BALANCE_SERVICE_ROOT_URL', '')
PENDING_ALLOCATION_NOTIFICATION_EMAIL = os.environ.get('PENDING_ALLOCATION_NOTIFICATION_EMAIL', '')
ACTIVATE_EXPIRE_ALLOCATION_FREQUENCY_IN_MINUTES = 30

# CELERY BEAT SCHEDULER
CELERY_BEAT_SCHEDULE = {
    'send-outage-reminders': {
        'task': 'chameleon_mailman.tasks.send_outage_reminders',
        'schedule': crontab(minute="*/{}".format(
            int(OUTAGE_REMINDER_FREQUENCY / 60))),
        'args': (OUTAGE_REMINDER_FREQUENCY, OUTAGE_EMAIL_REMINDER_TIMEDELTA)
    },
    'activate-expire-allocations': {
        'task': 'allocations.tasks.activate_expire_allocations',
        'schedule': crontab(minute="*/{}".format(
            int(ACTIVATE_EXPIRE_ALLOCATION_FREQUENCY_IN_MINUTES)))
    },
}

# Content-Security-Policy
CSP_FRAME_ANCESTORS = "'self'"  # Similar to X-Frame-Options: SAMEORIGIN
CSP_SCRIPT_SRC = ["'self'", 'https://www.google-analytics.com/', "'unsafe-inline'"]
CSP_FONT_SRC = ["'self'", 'https://fonts.gstatic.com/']
CSP_STYLE_SRC = ["'self'", 'https://fonts.googleapis.com/', "'unsafe-inline'"]
CSP_INCLUDE_NONCE_IN=['script-src']


# Federation new login experience
NEW_LOGIN_EXPERIENCE_COOKIE = 'new_login_experience'
