from django.contrib import admin
from functools import wraps
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from chameleon.models import PIEligibility
from util.keycloak_client import KeycloakClient
import re

def add_method(cls):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        setattr(cls, func.__name__, wrapper)
        return func
    return decorator

@add_method(get_user_model())
def pi_eligibility(self):
    try:
        return PIEligibility.objects.filter(requestor=self).latest('request_date').status
    except ObjectDoesNotExist:
        return 'Ineligible'

class PIEligibilityAdmin(admin.ModelAdmin):
    readonly_fields = ['requestor','request_date','user_metadata', 'reviewer','review_date']
    fields = ('requestor','request_date','user_metadata','status','review_date','reviewer','review_summary')
    ordering = ['-status','-request_date','-review_date']

    list_display = ('requestor','status','request_date')
    list_filter = ('status',)
    search_fields = ['requestor__username']

    def user_metadata(self, obj):
        keycloak_client = KeycloakClient()
        keycloak_user = keycloak_client.get_user_by_username(obj.requestor.username)

        if not keycloak_user:
            return None

        full_name = '{} {}'.format(keycloak_user['lastName'], keycloak_user['firstName'])
        email = keycloak_user['email']
        contents = [f'Name: {full_name}', f'Email: {email}']
        for key, val in keycloak_user['attributes'].items():
            if key not in ['joinDate']:
                #convert camelcase to separate out words
                key = re.sub("([A-Z])", " \\1", key).strip().capitalize()
                contents.append(f'{key}: {val}')

        return '\n'.join(contents)

admin.site.register(PIEligibility, PIEligibilityAdmin)
