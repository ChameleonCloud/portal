from django.contrib import admin
from .models import OpenIDStore, OpenIDNonce, OpenIDUserIdentity

# Register your models here.
admin.site.register(OpenIDStore)
admin.site.register(OpenIDNonce)
admin.site.register(OpenIDUserIdentity)