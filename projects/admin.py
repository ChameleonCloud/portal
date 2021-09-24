from django.contrib import admin

from projects.models import Invitation, Publication, Funding


class ProjectFields:
    def project_charge_code(self, model):
        """Obtain the charge_code attribute from the `project` relation."""
        project = getattr(model, "project", None)
        return getattr(project, "charge_code", None)


class PublicationAdmin(ProjectFields, admin.ModelAdmin):

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


class FundingAdmin(ProjectFields, admin.ModelAdmin):

    readonly_fields = [
        "project_charge_code",
    ]

    fields = (
        "project_charge_code",
        "is_active",
        "agency",
        "award",
        "grant_name",
    )

    ordering = ["project__charge_code"]
    list_display = ("project_charge_code", "agency", "award", "grant_name")

    def get_form(self, request, obj=None, **kwargs):
        form = super(FundingAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["award"].required = False
        return form


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Invitation)
admin.site.register(Funding, FundingAdmin)
