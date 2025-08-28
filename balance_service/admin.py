from balance_service.models import (
    ConfigVariable,
)
from django.contrib import admin
from django.contrib.admin import ModelAdmin


class ConfigVariableAdmin(ModelAdmin):
    list_display = ("key", "value", "flavor_id", "username", "project_charge_code")
    list_filter = ("key", "flavor_id", "username", "project_charge_code")
    search_fields = ("key", "flavor_id", "username", "project_charge_code")


admin.site.register(ConfigVariable, ConfigVariableAdmin)
