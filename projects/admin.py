from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from allocations.models import Allocation
from projects.models import (
    ChameleonPublication,
    Funding,
    Invitation,
    Project,
    Publication,
    PublicationSource,
)
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
        "project",
        "added_by_username",
    ]

    fields = (
        "submitted_date",
        "project",
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
        "reviewed_date",
        "reviewed_by",
        "reviewed_comment",
    )
    ordering = ["-status", "-id", "-year"]
    list_display = (
        "id",
        "title",
        "project",
        "year",
        "status",
    )
    list_filter = ["status", "year", "checked_for_duplicates", "publication_type"]
    search_fields = ["title", "project__charge_code", "author", "forum"]


class ChameleonPublicationAdmin(admin.ModelAdmin):
    fields = ("title", "ref")
    list_display = ("title", "ref")


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
    list_filter = ["status", "date_issued"]
    search_fields = ["project__charge_code"]
    actions = ["resend_invitation"]

    def invite_link(self, obj):
        if obj.status == Invitation.STATUS_ISSUED:
            url = obj.get_invite_url()
            return format_html(f'<a href="{url}" target="_blank">Invite Link</a>')
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

    def has_add_permission(self, request, obj=None):
        return False


class ProjectPublicationInline(admin.TabularInline):
    model = Publication
    exclude = ["tas_project_id"]
    extra = 1


class FundingInline(admin.TabularInline):
    model = Funding
    extra = 1


class InvitationInline(admin.TabularInline):
    model = Invitation
    readonly_fields = [
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

    def invite_link(self, obj):
        if obj.status == Invitation.STATUS_ISSUED:
            url = obj.get_invite_url()
            return format_html(f'<a href="{url}" target="_blank">Invite Link</a>')
        return ""

    def has_add_permission(self, req, obj):
        return False


class AllocationInline(admin.TabularInline):
    model = Allocation
    fields = [
        "date_requested",
        "status",
        "start_date",
        "expiration_date",
        "su_used",
        "su_allocated",
    ]
    readonly_fields = [
        "date_requested",
        "status",
        "start_date",
        "expiration_date",
        "su_used",
        "su_allocated",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProjectAdmin(admin.ModelAdmin):
    list_display = ["charge_code", "pi", "nickname", "title"]
    search_fields = ["charge_code", "pi__username", "pi__email", "nickname", "title"]
    list_filter = ["tag"]
    readonly_fields = [
        "charge_code_link",
        "automatically_tagged",
        "join_url",
    ]
    fields = [
        "charge_code_link",
        "title",
        "nickname",
        "description",
        "pi",
        "join_url",
    ]

    def charge_code_link(self, obj):
        return format_html(
            f'<a href="{reverse("projects:view_project", args=[obj.id])}" target="_blank">{obj.charge_code}</a>'
        )

    def join_url(self, obj):
        return format_html(
            f'<a href="{obj.join_link.get_url()}" target="_blank">Join Link</a>'
        )

    inlines = [
        ProjectPublicationInline,
        FundingInline,
        InvitationInline,
        AllocationInline,
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Project, ProjectAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ChameleonPublication, ChameleonPublicationAdmin)
admin.site.register(PublicationSource, PublicationSourceAdmin)
