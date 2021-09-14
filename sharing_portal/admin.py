from django.contrib import admin

from .models import Artifact, ArtifactVersion, Author, Label, DayPassRequest

admin.site.register(Artifact)
admin.site.register(ArtifactVersion)
admin.site.register(Author)
admin.site.register(Label)
admin.site.register(DayPassRequest)
