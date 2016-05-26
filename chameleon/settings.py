"""
Django settings for chameleon project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os
import django
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

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'chameleon.local',
    'chameleoncloud.org',
    'www.chameleoncloud.org',
    'www.tacc.chameleoncloud.org',
    'www.chameleon.tacc.utexas.edu',
    'dev.chameleon.tacc.utexas.edu',
]

# Application definition

INSTALLED_APPS = (
    ##
    # django-cms prereqs
    #
    'djangocms_admin_style',
    'djangocms_text_ckeditor',

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

    ##
    # django-cms
    #
    'cms',
    'mptt',
    'menus',
    'sekizai',
    'djangocms_style',
    'djangocms_column',
    'djangocms_file',
    'djangocms_flash',
    'djangocms_googlemap',
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
    'chameleon_openid',
    'chameleon_cms_integrations',
    'chameleon_mailman',
    'chameleon_token',
    'util',
    'tas',
    'djangoRT',
    'projects',
    'user_news',
    'djangular',
    'g5k_discovery',
    'cc_early_user_support',
    'allocations',
    'appliance_catalog',
    'webinar_registration'
)

MIDDLEWARE_CLASSES = (
    'djangular.middleware.DjangularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'termsandconditions.middleware.TermsAndConditionsRedirectMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'user_news.middleware.UserNewsNotificationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
)

ROOT_URLCONF = 'chameleon.urls'

WSGI_APPLICATION = 'chameleon.wsgi.application'


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

TIME_ZONE = 'UTC'

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


TEMPLATE_DIRS = (
    os.path.join(BASE_DIR,'chameleon','templates'),
)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

AUTHENTICATION_BACKENDS = (
    'tas.auth.TASBackend',
    'chameleon_openid.backend.OpenIDBackend',
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
        'console': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'default': {
            'handlers': ['console'],
            'level': 'DEBUG',
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
        'allocations': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'chameleon_mailman': {
            'handlers': ['console'],
            'level': 'INFO',
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

CMS_STYLE_NAMES = (
    ('enable-toc', _('Enable TOC (sidebar)')),
    ('sidebar-toc', _('Sidebar TOC')),
    ('header-toc', _('Header TOC')),
)

LANGUAGES = [
    ('en', 'English'),
]

MIGRATION_MODULES = {
    'cms': 'cms.migrations_django',
    'menus': 'menus.migrations_django',
    'djangocms_text_ckeditor': 'djangocms_text_ckeditor.migrations_django',
    'djangocms_column': 'djangocms_column.migrations_django',
    'djangocms_flash': 'djangocms_flash.migrations_django',
    'djangocms_googlemap': 'djangocms_googlemap.migrations_django',
    'djangocms_inherit': 'djangocms_inherit.migrations_django',
    'djangocms_style': 'djangocms_style.migrations_django',
    'djangocms_file': 'djangocms_file.migrations_django',
    'djangocms_link': 'djangocms_link.migrations_django',
    'djangocms_picture': 'djangocms_picture.migrations_django',
    'djangocms_teaser': 'djangocms_teaser.migrations_django',
    'djangocms_video': 'djangocms_video.migrations_django',
}


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
PIPELINE_COMPILERS = (
    'pipeline.compilers.sass.SASSCompiler',
)
PIPELINE_SASS_ARGUMENTS = '--update --compass --style compressed'
PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.slimit.SlimItCompressor'

# wildcards put the files in alphabetical order
PIPELINE_CSS = {
    'main': {
        'source_filenames': (
            'styles/main.scss',
            'styles/corner-ribbon.css',
            'djangoRT/css/djangoRT.css',
            'projects/css/projects.scss',
            ),
        'output_filename': 'styles/main.css',
    },
}

PIPELINE_JS = {
    'all': {
        'source_filenames': (
            'bower_components/jquery/dist/jquery.js',
            'bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js',
            'bower_components/toc/dist/toc.js',
            'scripts/auto-table-of-contents.js',
            'djangoRT/js/djangoRT.js',
        ),
        'output_filename': 'scripts/all.js'
    }
}

# compress when collect static
STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

TEMPLATE_CONTEXT_PROCESSORS = django.conf.global_settings.TEMPLATE_CONTEXT_PROCESSORS

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    'chameleon.context_processors.google_analytics',
    'sekizai.context_processors.sekizai',
    'cms.context_processors.cms_settings',
)


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
DEFAULT_TERMS_SLUG = 'user-terms'
ACCEPT_TERMS_PATH = '/terms/accept/'
TERMS_EXCLUDE_URL_PREFIX_LIST = {'/admin', '/terms'}
TERMS_EXCLUDE_URL_LIST = {'/', '/termsrequired/', '/logout/', '/securetoo/'}
MULTIPLE_ACTIVE_TERMS = False # Multiple kinds of T&Cs active at once (like site-terms, and contributor-terms).


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
        'url': 'https://portal.geni.net/secure/project.php?project_id=97762ef8-86ea-4212-b41a-ac5d75467c16',
    },
    'chameleon': {
        'id': '26427',
        'name': 'GENI-Federation',
        'url': 'https://www.chameleoncloud.org/user/projects/26427/'
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
