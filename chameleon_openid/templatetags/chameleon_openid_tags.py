from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('chameleon_openid/login_options.html')
def openid_login_options(openid_providers=None):
    if not openid_providers:
        openid_providers = settings.OPENID_PROVIDERS

    return {
        'providers': openid_providers
    }
