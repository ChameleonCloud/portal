from django.contrib import admin

from .models import Artifact, ArtifactVersion, Author, Label

admin.site.register(Artifact)
admin.site.register(ArtifactVersion)
admin.site.register(Author)
admin.site.register(Label)
