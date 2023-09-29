from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from projects.models import (ChameleonPublication, Funding, Invitation,
                             Publication, PublicationSource)
from projects.views import resend_invitation


class ProjectFields:
    def project_charge_code(self, model):
        """Obtain the charge_code attribute from the `project` relation."""
        project = getattr(model, "project", None)
        return getattr(project, "charge_code", None)


class PublicationSourceInline(admin.TabularInline):
    model = PublicationSource
    extra = 0


class PublicationAdmin(ProjectFields, admin.ModelAdmin):
    inlines = (PublicationSourceInline,)

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
        "checked_for_duplicates",
    )
    ordering = ["-status", "-id", "-year"]
    list_display = (
        "id",
        "title",
        "project_charge_code",
        "year",
        "status",
    )


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
        """Obtain the publication id attribute from the `publication` relation"""
        publication = getattr(model, "publication", None)
        return getattr(publication, "id", None)

    def publication_title(self, model):
        """Obtain the publication title attribute from the `publication` relation"""
        publication = getattr(model, "publication", None)
        return getattr(publication, "title", None)


class PublicationSourceAdmin(PublicationFields, admin.ModelAdmin):
    readonly_fields = [
        "citation_count",
    ]

    fields = (
        "name",
        "publication",
        "citation_count",
        "is_found_by_algorithm",
        "cites_chameleon",
        "acknowledges_chameleon",
        "entry_created_date",
    )

    list_display = (
        "name",
        "citation_count",
        "publication",
        "entry_created_date",
    )


class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email_address", "status", "date_issued", "expiry_list_display"]
    fields = [
        "project",
        "email_address",
        "status",
        "invite_link",
        "user_issued",
        "date_issued",
        "user_accepted",
        "date_accepted",
        "date_expires",
        "duration",
    ]
    readonly_fields = [
        "invite_link",
        "user_issued",
        "date_issued",
        "email_address",
        "user_accepted",
        "date_accepted",
        "status",
    ]
    actions = ['resend_invitation']

    def invite_link(self, obj):
        if obj.status == Invitation.STATUS_ISSUED:
            url = obj.get_invite_url()
            return format_html(
                f'<a href="{url}" target="_blank">Invite Link</a>'
            )
        return ""

    @admin.display(description="Expiry")
    def expiry_list_display(self, obj):
        return f"{'EXPIRED' if obj._is_expired() else obj.date_expires}"

    def resend_invitation(self, request, invitations):
        user_issued = request.user
        for invitation in invitations:
            resend_invitation(invitation.id, user_issued, request)
            self.message_user(request, f"Invitations resent by {user_issued}.")

    resend_invitation.short_description = "Resend Invitations"


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(Funding, FundingAdmin)
admin.site.register(ChameleonPublication, ChameleonPublicationAdmin)
admin.site.register(PublicationSource, PublicationSourceAdmin)
