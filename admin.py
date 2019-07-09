from django.contrib import admin

from .models import Artifact, Author, Label

admin.site.register(Artifact)
admin.site.register(Author)
admin.site.register(Label)

# Register your models here.
