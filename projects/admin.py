from datetime import date
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe

from chameleon.tasks import AdminTaskManager
from djangoRT import rtUtil
from projects.user_publication.deduplicate import get_originals_for_duplicate_pub
from projects.user_publication.publications import (
    import_pubs_google_scholar_task,
    import_pubs_scopus_task,
    import_pubs_semantic_scholar_task,
)

from allocations.models import Allocation
from projects.models import (
    ChameleonPublication,
    Funding,
    Invitation,
    Project,
    Publication,
    PublicationDuplicate,
    PublicationSource,
)
from projects.views import resend_invitation

import logging

LOG = logging.getLogger(__name__)


class ProjectFields:
    def project_charge_code(self, model):
        """Obtain the charge_code attribute from the `project` relation."""
        project = getattr(model, "project", None)
        return getattr(project, "charge_code", None)


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


class PublicationSourceInline(admin.TabularInline):
    model = PublicationSource
    extra = 0


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


class PotentialDuplicateFilter(admin.SimpleListFilter):
    title = "Is a Potential Duplicate"
    parameter_name = "is_potential_duplicate_of"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(
                checked_for_duplicates=False,
                status=Publication.STATUS_SUBMITTED,
            ).filter(
                id__in=[
                    pub.id
                    for pub in queryset
                    if len(get_originals_for_duplicate_pub(pub)) > 0
                ]
            )
        if self.value() == "no":
            return queryset.filter(
                checked_for_duplicates=False,
                status=Publication.STATUS_SUBMITTED,
            ).exclude(
                id__in=[
                    pub.id
                    for pub in queryset
                    if len(get_originals_for_duplicate_pub(pub)) > 0
                ]
            )


class DuplicateOfDuplicatePublicationInline(admin.TabularInline):
    model = PublicationDuplicate
    fk_name = "duplicate"
    extra = 0
    verbose_name = "Duplicate of publication"

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj):
        return False


class DuplicatesDuplicatePublicationInline(admin.TabularInline):
    model = PublicationDuplicate
    fk_name = "original"
    extra = 0
    readonly_fields = ["original"]
    verbose_name = "Duplicated by publication"

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj):
        return False


class PublicationAdmin(ProjectFields, admin.ModelAdmin):
    inlines = (
        PublicationSourceInline,
        DuplicatesDuplicatePublicationInline,
        DuplicateOfDuplicatePublicationInline,
    )

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "title",
                    "submitted_date",
                    "project",
                    "publication_type",
                    "forum",
                    "year",
                    "month",
                    "author",
                    "doi",
                    "link",
                    "clickable_link",
                    "added_by_username",
                    "ticket_id",
                    "ticket_link",
                ],
            },
        ),
        (
            "Review",
            {
                "fields": [
                    "status",
                    "reviewed_date",
                    "reviewed_by",
                    "reviewed_comment",
                    "potential_duplicate_of",
                    "checked_for_duplicates",
                ]
            },
        ),
        (
            "Advanced",
            {
                "classes": ["collapse"],
                "fields": [
                    "bibtex_source",
                ],
            },
        ),
    ]
    readonly_fields = [
        "project",
        "added_by_username",
        "potential_duplicate_of",
        "clickable_link",
        "ticket_link",
    ]
    ordering = ["-status", "-id", "-year"]
    list_display = (
        "id",
        "short_title",
        "project",
        "year",
        "checked_for_duplicates",
        "status",
        "clickable_link",
    )
    list_filter = [
        PotentialDuplicateFilter,
        "status",
        "year",
        "checked_for_duplicates",
        "publication_type",
    ]
    search_fields = ["title", "project__charge_code", "author", "forum"]

    actions = ["mark_checked_for_duplicates", "mark_approved"]

    change_list_template = "admin/import_publication_changelist.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_managers = [
            AdminTaskManager(self.admin_site, "import_scopus", import_pubs_scopus_task),
            AdminTaskManager(
                self.admin_site,
                "import_semantic_scholar",
                import_pubs_semantic_scholar_task,
            ),
            AdminTaskManager(
                self.admin_site, "import_gscholar", import_pubs_google_scholar_task
            ),
        ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "reviewed_by":
            kwargs["queryset"] = get_user_model().objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path(
                "<int:duplicate_id>/create-duplicate/<int:original_id>",
                self.admin_site.admin_view(self.create_duplicate),
                name="projects_create_publication_duplicate",
            ),
        ]
        for task_manager in self.task_managers:
            urls += task_manager.get_urls()
        return urls

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["task_managers"] = self.task_managers
        return super().changelist_view(request, extra_context=extra_context)

    def potential_duplicate_of(self, obj):
        duplicates = get_originals_for_duplicate_pub(obj)
        if not duplicates:
            return "No similar publications found"

        links = []
        for pub in duplicates:
            create_url = reverse(
                "admin:projects_create_publication_duplicate", args=[obj.pk, pub.pk]
            )
            links.append(
                f"""
                <li>
                <a href="{reverse("admin:projects_publication_change", args=[pub.pk])}">{str(pub)})</a>
                    <a class="btn" href="#" onclick="createDuplicate('{create_url}', '{pub.pk}')">
                        Mark Duplicate
                    </a>
                </li>
                """
            )
        links_html = "".join(links)
        script_html = """
            <script>
                function createDuplicate(url, title) {
                if (confirm(`Mark as duplicate of "${title}"?`)) {
                    fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                    .then(response => {
                        if (response.ok) {
                            alert(`Successfully marked this pub as a duplicate.`);
                            window.location.reload();
                        } else {
                            alert(`Failed to mark duplicate.`);
                        }
                    });
                }
            }
            </script>
        """
        return mark_safe(
            f"""
            {script_html}
            <ul>{links_html}</ul>
        """
        )

    potential_duplicate_of.short_description = "Is Potential Duplicate Of"

    def short_title(self, obj):
        max_length = 50
        if len(obj.title) > max_length:
            return f"{obj.title[:max_length]}..."
        return obj.title

    def clickable_link(self, obj):
        if obj.link:
            return mark_safe(f'<a href="{obj.link}" target="_blank">{obj.link}</a>')
        return ""

    def ticket_link(self, obj):
        if obj.ticket_id:
            link = f"https://consult.tacc.utexas.edu/Ticket/Display.html?id={obj.ticket_id}"
            return mark_safe(f'<a href="{link}" target="_blank">{link}</a>')
        return ""

    @admin.action(description="Mark selected as checked for duplicates")
    def mark_checked_for_duplicates(self, request, queryset):
        updated_count = queryset.update(checked_for_duplicates=True)
        self.message_user(
            request,
            f"{updated_count} publication(s) marked as checked for duplicates.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected as approved")
    def mark_approved(self, request, queryset):
        updated_count = queryset.update(
            status=Publication.STATUS_APPROVED,
            checked_for_duplicates=True,
            reviewed_by=request.user,
            reviewed_date=date.today(),
        )
        self.message_user(
            request,
            f"{updated_count} publication(s) marked as approved.",
            messages.SUCCESS,
        )

    def create_duplicate(self, request, duplicate_id, original_id):
        duplicate = Publication.objects.get(pk=duplicate_id)
        original = Publication.objects.get(pk=original_id)

        PublicationDuplicate.objects.create(duplicate=duplicate, original=original)
        duplicate.checked_for_duplicates = True
        duplicate.status = Publication.STATUS_DUPLICATE
        duplicate.checked_for_duplicates = True
        duplicate.reviewed_by = request.user
        duplicate.reviewed_date = date.today()
        public_publication_url = f"https://chameleoncloud.org/user/projects/chameleon-used-research/#pub-{original.pk}"
        duplicate.reviewed_comment = f"Marked as a duplicate of '{original.title}'. See {public_publication_url}."
        duplicate.save()
        self.message_user(
            request,
            f"Marked '{duplicate.title}' as a duplicate of '{original.title}'.",
            messages.SUCCESS,
        )
        return HttpResponseRedirect(reverse("admin:projects_publication_changelist"))

    def save_model(self, request, obj, form, change):
        if (
            obj.status != Publication.STATUS_SUBMITTED
            and obj.ticket_id
            and obj.ticket_id
        ):
            rt = rtUtil.DjangoRt()
            rt.closeTicket(obj.ticket_id)


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ChameleonPublication, ChameleonPublicationAdmin)
admin.site.register(PublicationSource, PublicationSourceAdmin)
