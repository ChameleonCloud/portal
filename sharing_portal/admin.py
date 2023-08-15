from django.contrib import admin

from .models import DaypassRequest, FeaturedArtifact, ArtifactBadge, Badge


class ArtifactBadgeAdmin(admin.ModelAdmin):
    list_display = ["get_badge_name", "artifact_uuid", "status", "requested_on"]

    def get_badge_name(self, obj):
        return obj.badge.name

    get_badge_name.short_description = "Badge Name"


admin.site.register(DaypassRequest)
admin.site.register(FeaturedArtifact)
admin.site.register(ArtifactBadge, ArtifactBadgeAdmin)
admin.site.register(Badge)
