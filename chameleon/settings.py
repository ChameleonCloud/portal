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

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + ('django.core.context_processors.request',)

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

    'password_reset',

    'django_countries',

    # local
    'about',
    'news',
    'status',
    'documentation',
    'help',
    'person',
    'allocation',
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


HELPDESK_VIEW_A_TICKET_PUBLIC = False
HELPDESK_SUBMIT_A_TICKET_PUBLIC = False

import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType, PosixGroupType
#AUTH_LDAP_START_TLS = True
AUTH_LDAP_GLOBAL_OPTIONS = {
 ldap.OPT_X_TLS_REQUIRE_CERT: False,
 ldap.OPT_REFERRALS: False,
}
# Baseline configuration.
AUTH_LDAP_SERVER_URI = "ldap://129.114.33.180"
AUTH_LDAP_BIND_DN = "cn=portal,dc=chameleoncloud,dc=org"
AUTH_LDAP_BIND_PASSWORD = "t3mp0rArY"
AUTH_LDAP_USER_SEARCH = LDAPSearch("ou=people,dc=chameleoncloud,dc=org", ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
# or perhaps:
# AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=users,dc=example,dc=com"
AUTH_LDAP_ALWAYS_UPDATE_USER = True
# Set up the basic group parameters.
AUTH_LDAP_GROUP_SEARCH = LDAPSearch("ou=group,dc=chameleoncloud,dc=org",
                                    ldap.SCOPE_SUBTREE, "(objectClass=posixGroup)"
)
# set group type
AUTH_LDAP_GROUP_TYPE = PosixGroupType()
# Simple group restrictions
#~ AUTH_LDAP_REQUIRE_GROUP = "cn=enabled,ou=django,ou=group,dc=example,dc=com"
#~ AUTH_LDAP_DENY_GROUP = "cn=disabled,ou=django,ou=group,dc=example,dc=com"
# Populate the Django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
 "first_name": "givenName",
 "last_name": "sn",
 "email": "mail"
}
#~ AUTH_LDAP_PROFILE_ATTR_MAP = {
 #~ "employee_number": "employeeNumber"
#~ }
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
# "is_active": "cn=active,ou=group,dc=parent,dc=ssischool,dc=org",
# "is_staff": "cn=staff,ou=group,dc=chameleoncloud,dc=org",
# "is_superuser": "cn=superuser,ou=group,dc=parent,dc=ssischool,dc=org"
}
#~ AUTH_LDAP_PROFILE_FLAGS_BY_GROUP = {
 #~ "is_awesome": "cn=awesome,ou=django,ou=group,dc=example,dc=com",
#~ }
# important! to use the group's permission
AUTH_LDAP_MIRROR_GROUPS = True
# Use LDAP group membership to calculate group permissions.
AUTH_LDAP_FIND_GROUP_PERMS = True
# Cache group memberships for an hour to minimize LDAP traffic
AUTH_LDAP_CACHE_GROUPS = True
AUTH_LDAP_GROUP_CACHE_TIMEOUT = 2

import logging
logger = logging.getLogger('django_auth_ldap')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)
