from django.contrib import admin

from projects.models import Invitation, Publication


class PublicationAdmin(admin.ModelAdmin):

    readonly_fields = [
        "project_charge_code",
        "added_by_username",
        "entry_created_date",
    ]

    fields = (
        "project_charge_code",
        "publication_type",
        "forum",
        "title",
        "year",
        "month",
        "author",
        "bibtex_source",
        "link",
        "added_by_username",
        "entry_created_date",
    )

    ordering = ["project__charge_code", "-year", "-entry_created_date"]
    list_display = ("title", "project_charge_code", "year", "entry_created_date")

    def project_charge_code(self, obj):
        if obj.project:
            return obj.project.charge_code
        else:
            return None


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Invitation)
