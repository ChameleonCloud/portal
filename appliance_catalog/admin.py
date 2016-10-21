from django.contrib import admin
from .models import Keyword, Appliance, ApplianceTagging

def make_reviewed(modelAdmin, request, queryset):
    queryset.update(needs_review=False)

make_reviewed.short_description = "Appliance has been reviewed"

class ApplianceAdmin(admin.ModelAdmin):
    list_display = ("name", "short_description", "author_name", "needs_review", "project_supported")
    actions = [make_reviewed]

class KeywordAdmin(admin.ModelAdmin):
    pass

class ApplianceTaggingAdmin(admin.ModelAdmin):
    pass

admin.site.register(Keyword, KeywordAdmin)
admin.site.register(Appliance, ApplianceAdmin)
admin.site.register(ApplianceTagging, ApplianceTaggingAdmin)
