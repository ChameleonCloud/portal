from django.contrib import admin
from .models import Keyword, Appliance, ApplianceTagging

class ApplianceAdmin(admin.ModelAdmin):
    list_display = ("name", "short_description", "author_name", "needs_review", "project_supported")

class KeywordAdmin(admin.ModelAdmin):
    pass

class ApplianceTaggingAdmin(admin.ModelAdmin):
    pass

admin.site.register(Keyword, KeywordAdmin)
admin.site.register(Appliance, ApplianceAdmin)
admin.site.register(ApplianceTagging, ApplianceTaggingAdmin)
