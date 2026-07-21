from balance_service.models import (
    ConfigVariable,
)
from django.contrib import admin
from django.contrib.admin import ModelAdmin


class ConfigVariableAdmin(ModelAdmin):
    list_display = (
        "key",
        "value",
        "flavor_id",
        "username",
        "project_charge_code",
        "region",
    )
    list_filter = ("key", "flavor_id", "username", "project_charge_code", "region")
    search_fields = ("key", "flavor_id", "username", "project_charge_code", "region")


admin.site.register(ConfigVariable, ConfigVariableAdmin)
