from django.contrib import admin

from projects.models import Invitation, Publication, Funding, ChameleonPublication, PublicationSource


class ProjectFields:
    def project_charge_code(self, model):
        """Obtain the charge_code attribute from the `project` relation."""
        project = getattr(model, "project", None)
        return getattr(project, "charge_code", None)


class PublicationAdmin(ProjectFields, admin.ModelAdmin):

    readonly_fields = [
        "project_charge_code",
        "added_by_username",
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
        "doi",
        "link",
        "added_by_username",
        "status",
        "reviewed",
    )
    ordering = ["project__charge_code", "-year"]
    list_display = ("title", "project_charge_code", "year",)


class ChameleonPublicationAdmin(admin.ModelAdmin):
    fields = ("title", "ref")
    list_display = ("title", "ref")


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


class PublicationFields:
    def publication_id(self, model):
        """Obtain the publication id attribute from the `publication` relation """
        publication = getattr(model, "publication", None)
        return getattr(publication, "id", None)

    def publication_title(self, model):
        """Obtain the publication title attribute from the `publication` relation """
        publication = getattr(model, "publication", None)
        return getattr(publication, "title", None)


class PublicationSourceAdmin(PublicationFields, admin.ModelAdmin):
    readonly_fields = [
        "citation_count"
    ]

    fields = (
        "name",
        "publication",
        "citation_count",
        "found_by_algorithm",
        "is_cited",
        "is_acknowledged",
        "entry_created_date",
    )

    list_display = (
        "name",
        "citation_count",
        "publication",
        "entry_created_date",
    )


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Invitation)
admin.site.register(Funding, FundingAdmin)
admin.site.register(ChameleonPublication, ChameleonPublicationAdmin)
admin.site.register(PublicationSource, PublicationSourceAdmin)
