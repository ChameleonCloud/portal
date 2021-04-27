from django.contrib import admin

from projects.models import Invitation, Publication

admin.site.register(Publication)
admin.site.register(Invitation)
