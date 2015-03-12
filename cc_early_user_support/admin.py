from django.contrib import admin
from . import models
from . import forms

# Register your models here.
@admin.register(models.EarlyUserRequest)
class EarlyUserRequestAdmin(admin.ModelAdmin):
    form = forms.EarlyUserRequestAdminForm
    list_display = ('user_nice_name', 'created', 'request_status')
    list_filter = ('request_status',)

    def user_nice_name(self, obj):
        return obj.user.get_full_name()

    user_nice_name.short_description = 'Name'
