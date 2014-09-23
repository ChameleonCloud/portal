"""
Django settings for chameleon project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

from django.conf import global_settings

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'g^j%2+ry^44nsni4am7*%ypfb3$dm$s=9+lpy$&^q6w3zcmvnc'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = [os.path.join(BASE_DIR,'chameleon','templates')]

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS
TEMPLATE_CONTEXT_PROCESSORS += ('django.core.context_processors.request',)
#TEMPLATE_CONTEXT_PROCESSORS += ("allauth.account.context_processors.account",)
#TEMPLATE_CONTEXT_PROCESSORS += ("allauth.socialaccount.context_processors.socialaccount",)

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # humanize used by helpdisk
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # to convert sass to css
    'pipeline',

    # django-simple-menu
    'menu',

    'markdown_deux',
    'bootstrapform',
    'helpdesk',

    # allauth seems to want sites
    #'django.contrib.sites',
    #'allauth',
    #'allauth.account',

    #'password_reset',

    'openstack_auth',

    'django_countries',

    # local
    'about',
    'news',
    'status',
    'documentation',
    'help',
    'user',
    'allocation',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
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

#TIME_ZONE = 'UTC'
TIME_ZONE = 'America/Chicago'

USE_I18N = True

USE_L10N = True

USE_TZ = True


from markdown_deux.conf.settings import MARKDOWN_DEUX_DEFAULT_STYLE
MARKDOWN_DEUX_DEFAULT_STYLE["extras"]["wiki-tables"] = None

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = '/var/www/chameleoncloud.org/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
    '/var/www/static/',
)

MEDIA_ROOT = os.path.join(BASE_DIR,"media")
MEDIA_URL = '/media/'

#STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'
STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_COMPILERS = ( 
    'pipeline.compilers.sass.SASSCompiler',
)   

PIPELINE_CSS_COMPRESSOR = None

# wildcards put the files in alphabetical order
PIPELINE_CSS = { 
    'main': {
        'source_filenames': (
            'scss/main.scss',
            ),
        'output_filename': 'css/main.css',
    },
    'main_fa': {
        'source_filenames': (
            'scss/vendor/fontawesome/font_awesome.scss',
            'scss/main.scss',
            ),
        'output_filename': 'css/main.css',
    },
}

# django-password-reset
DEFAULT_FROM_EMAIL = ""
# django.core.mail
EMAIL_HOST = ""
#EMAIL_PORT = 
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
# print emails to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

HELPDESK_VIEW_A_TICKET_PUBLIC = False
HELPDESK_SUBMIT_A_TICKET_PUBLIC = True

#AUTH_USER_MODEL = "user.ChameleonUser"
#AUTH_USER_MODEL = "openstack_auth.user.User"

import logging
#logger = logging.getLogger('django_auth_ldap')
logger = logging.getLogger('openstack_auth')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

#AUTHENTICATION_BACKENDS = (
#    'django_auth_ldap.backend.LDAPBackend',
#    'django.contrib.auth.backends.ModelBackend',
#    "allauth.account.auth_backends.AuthenticationBackend",
#)

AUTHENTICATION_BACKENDS = ('openstack_auth.backend.KeystoneBackend',)
OPENSTACK_KEYSTONE_URL = "http://129.114.33.181:5000/v2.0"
#AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

# for django-allauth
SITE_ID = 1

LOGIN_REDIRECT_URL = "/"

ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# to get custom information about the user:
#ACCOUNT_SIGNUP_FORM_CLASS = "user.forms.SignupForm"

# during django reloads and an active user is logged in, the monkey 
# patch below will not otherwise be applied in time - resulting in developers 
# appearing to be logged out.In typical production deployments this section 
# below may be omitted, though it should not be harmful
from openstack_auth import utils as auth_utils
auth_utils.patch_middleware_get_user()
