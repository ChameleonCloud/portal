from django.contrib import admin

from .models import DaypassRequest, FeaturedArtifact, ArtifactBadge, Badge

admin.site.register(DaypassRequest)

admin.site.register(FeaturedArtifact)

admin.site.register(ArtifactBadge)
admin.site.register(Badge)
