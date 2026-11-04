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
        "resource_type",
        "resource_class",
        "resource_name",
    )
    list_filter = (
        "key",
        "flavor_id",
        "username",
        "project_charge_code",
        "region",
        "resource_type",
        "resource_class",
    )
    search_fields = (
        "key",
        "flavor_id",
        "username",
        "project_charge_code",
        "region",
        "resource_class",
        "resource_name",
    )


admin.site.register(ConfigVariable, ConfigVariableAdmin)
