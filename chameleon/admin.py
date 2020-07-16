from django.contrib import admin
from functools import wraps
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from chameleon.models import PIEligibility

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
    readonly_fields = ['requestor','request_date','reviewer','review_date']
    fields = ('requestor','request_date','status','review_date','reviewer','review_summary')
    ordering = ['-request_date','-review_date']

    list_display = ('requestor','status','request_date')

admin.site.register(PIEligibility, PIEligibilityAdmin)