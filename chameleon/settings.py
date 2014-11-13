"""
Django settings for chameleon project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os
import django

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&q*yhkpinzej(zcs$hq-g6@^y()d2h&36!m)8-5o3@d-4rth(b'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # contrib
    'pipeline',
    'menu',
    'markdown_deux',

    # custom
    'site_menu',
    'util',
    'tas',
    'documentation',
    'djangoRT',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'chameleon.urls'

WSGI_APPLICATION = 'chameleon.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = '/var/www/chameleoncloud.org/static'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    '/var/www/static/',
)

TEMPLATE_DIRS = [os.path.join(BASE_DIR,'chameleon','templates')]

AUTHENTICATION_BACKENDS = (
    'tas.auth.TASBackend',
)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/user/dashboard'

#####
#
# Logger config
#
#####
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'requests': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/requests.log',
        },
        'tas': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/tas.log',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['requests'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'tas': {
            'handlers': ['tas'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

#####
#
# Pipeline config
#
#####
PIPELINE_COMPILERS = (
    'pipeline.compilers.sass.SASSCompiler',
)

PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.uglifyjs.UglifyJSCompressor'

# wildcards put the files in alphabetical order
PIPELINE_CSS = {
    'main': {
        'source_filenames': (
            'scss/main.scss',
            'djangoRT/css/djangoRT.css',
            ),
        'output_filename': 'css/main.css',
    },
}

PIPELINE_JS = {
    'all': {
        'source_filenames': (
            'bower_components/jquery/dist/jquery.js',
            'bower_components/bootstrap-sass-official/assets/javascripts/bootstrap.js',
            'djangoRT/js/djangoRT.js',
        ),
        'output_filename': 'scripts/all.js'
    }
}

TEMPLATE_CONTEXT_PROCESSORS = django.conf.global_settings.TEMPLATE_CONTEXT_PROCESSORS

# include request for django-simple-menu
TEMPLATE_CONTEXT_PROCESSORS += ('django.core.context_processors.request',)

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
