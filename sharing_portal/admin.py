from django.contrib import admin

from .models import DaypassRequest, FeaturedArtifact, ArtifactBadge

admin.site.register(DaypassRequest)

admin.site.register(FeaturedArtifact)

admin.site.register(ArtifactBadge)
