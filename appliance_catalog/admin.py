from django.contrib import admin
import django.forms as forms
from .models import Keyword, Appliance, ApplianceTagging


def make_reviewed(modelAdmin, request, queryset):
    queryset.update(needs_review=False)


make_reviewed.short_description = "Appliance has been reviewed"


class ApplianceAdminForm(forms.ModelForm):
    def clean_chi_tacc_appliance_id(self):
        if self.cleaned_data["chi_tacc_appliance_id"] == "":
            return None
        return self.cleaned_data["chi_tacc_appliance_id"]

    def clean_chi_uc_appliance_id(self):
        if self.cleaned_data["chi_uc_appliance_id"] == "":
            return None
        return self.cleaned_data["chi_uc_appliance_id"]

    def clean_kvm_tacc_appliance_id(self):
        if self.cleaned_data["kvm_tacc_appliance_id"] == "":
            return None
        return self.cleaned_data["kvm_tacc_appliance_id"]


class ApplianceTaggingInline(admin.TabularInline):
    model = ApplianceTagging


class ApplianceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_date",
        "short_description",
        "author_name",
        "needs_review",
        "project_supported",
    )
    ordering = ["-created_date"]
    list_filter = ["needs_review", "project_supported"]
    actions = [make_reviewed]
    inlines = [ApplianceTaggingInline]
    form = ApplianceAdminForm


class KeywordAdmin(admin.ModelAdmin):
    pass


class ApplianceTaggingAdmin(admin.ModelAdmin):
    pass


admin.site.register(Keyword, KeywordAdmin)
admin.site.register(Appliance, ApplianceAdmin)
