from django.contrib import admin
from .models import Token


class TokenAdmin(admin.ModelAdmin):
    exclude = ['token']

admin.site.register(Token, TokenAdmin)
