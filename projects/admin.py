from datetime import date
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe

from chameleon.tasks import AdminTaskManager
from djangoRT import rtUtil
from projects.forms import AddBibtexPublicationForm
from projects.pub_views import create_pubs_from_bibtext_string
from projects.user_publication import utils
from projects.user_publication.deduplicate import get_originals_for_duplicate_pub
from projects.user_publication.publications import (
    import_pubs_science_direct_task,
    import_pubs_scopus_task,
    import_pubs_semantic_scholar_task,
    import_pubs_openalex_task,
    update_citations_task,
)

from allocations.models import Allocation
from projects.models import (
    ChameleonPublication,
    Forum,
    ForumAlias,
    Funding,
    Invitation,
    Project,
    Publication,
    PublicationCitation,
    PublicationQuery,
    PublicationSource,
    RawPublication,
)
from projects.user_publication.utils import PublicationUtils
from projects.views import resend_invitation

from projects.user_publication.utils import (
    RawPublicationSource,
)

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
    fields = (
        "name",
        "is_found_by_algorithm",
        "cites_chameleon",
        "acknowledges_chameleon",
        "approved_with",
        "entry_created_date",
        "citation_count",
    )


class RawPublicationInline(admin.TabularInline):
    model = RawPublication
    extra = 0
    fields = (
        "admin_link",
        "name",
        "is_found_by_algorithm",
        "cites_chameleon",
        "acknowledges_chameleon",
        "approved_with",
        "entry_created_date",
        "citation_count",
    )
    readonly_fields = ("admin_link",)

    def admin_link(self, obj):
        if not obj.pk:
            return "(save first)"
        url = reverse(
            "admin:projects_rawpublication_change",  # CHANGE THIS
            args=[obj.pk],
        )
        return format_html('<a href="{}" target="_blank">Open</a>', url)

    admin_link.short_description = "Edit"


class ChameleonPublicationRawPublicationInline(admin.TabularInline):
    model = ChameleonPublication.raw_publications.through
    extra = 0
    can_delete = False
    verbose_name = "Raw Publication"
    verbose_name_plural = "Raw Publications"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ChameleonPublicationAdmin(admin.ModelAdmin):
    fields = ("title", "semantic_scholar_ref", "scopus_ref", "openalex_ref")
    list_display = ("title", "semantic_scholar_ref", "scopus_ref", "openalex_ref")
    inlines = [ChameleonPublicationRawPublicationInline]


class PublicationCitationInline(admin.StackedInline):
    model = PublicationCitation
    fields = (
        "scopus_source_id",
        "scopus_citation_count",
        "semantic_scholar_source_id",
        "semantic_scholar_citation_count",
    )
    can_delete = False
    verbose_name = "Citation"
    verbose_name_plural = "Citations"


class QueryRawPublicationInline(admin.TabularInline):
    model = RawPublication.publication_queries.through
    extra = 0
    can_delete = False
    verbose_name = "Raw Publication"
    verbose_name_plural = "Raw Publications"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class PublicationQueryAdmin(admin.ModelAdmin):
    list_display = ("source_type", "query")
    inlines = [QueryRawPublicationInline]


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
        "source_id",
        "publication",
        "citation_count",
        "entry_created_date",
    )

    list_display = (
        "id",
        "name",
        "source_id",
        "citation_count",
        "publication",
        "entry_created_date",
    )

    list_filter = (
        "name",
        "entry_created_date",
    )


class RawPublicationAdmin(PublicationFields, admin.ModelAdmin):
    list_display = (
        "id",
        "entry_created_date",
        "name",
        "source_id",
        "citation_count",
        "publication",
    )

    list_filter = (
        "name",
        "entry_created_date",
    )

    autocomplete_fields = ("publication",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "publication":
            kwargs["queryset"] = Publication.objects.order_by(
                "-status",
                "title",
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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


class PublicationAdmin(ProjectFields, admin.ModelAdmin):
    inlines = (RawPublicationInline, PublicationCitationInline)

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "title",
                    "submitted_date",
                    "potential_project",
                    "publication_type",
                    "forum",
                    # "year",
                    # "month",
                    "author",
                    "doi",
                    # "link",
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
            "Source comparison",
            {
                "fields": [
                    "source_comparison",
                ]
            },
        ),
    ]
    readonly_fields = [
        "project",
        "added_by_username",
        "potential_duplicate_of",
        "potential_project",
        "clickable_link",
        "ticket_link",
        "source_comparison",
        "source_count",
    ]
    ordering = ["-status", "-id", "-year"]
    list_display = (
        "id",
        "submitted_date",
        "short_title",
        "project",
        "year",
        "checked_for_duplicates",
        "status",
        "source_count",
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
                self.admin_site,
                "import_science_direct",
                import_pubs_science_direct_task,
            ),
            AdminTaskManager(
                self.admin_site,
                "import_openalex",
                import_pubs_openalex_task,
            ),
            AdminTaskManager(
                self.admin_site, "update_citations", update_citations_task
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

        if request.method == "POST":
            form = AddBibtexPublicationForm(request.POST, is_admin=True)
            if form.is_valid():
                # bibtex_data = form.cleaned_data["bibtex"]
                new_pubs = create_pubs_from_bibtext_string(
                    form.cleaned_data["bibtex_string"],
                    project=None,
                    username="admin",
                    source=form.cleaned_data["source"],
                    cites_chameleon_pub_id=form.cleaned_data["cites_chameleon_pub"],
                    found_with_query_id=form.cleaned_data["found_with_query"],
                )
                LOG.info(f"Created {len(new_pubs)} new publications from bibtex.")
                duplicates_count = 0
                new_pubs_count = 0
                for pub in new_pubs:
                    matches = utils.get_publications_with_same_attributes(
                        pub, Publication
                    )
                    matches = [m for m in matches if m.id != pub.id]
                    if matches:
                        LOG.info(
                            f"Found duplicate publication for {pub.id}, merging into {matches[0].id}"
                        )
                        target_pub = matches[0]
                        source = pub.raw_sources.first()
                        if source:
                            utils.add_source_to_pub(
                                target_pub,
                                RawPublicationSource(
                                    source_name=source.name,
                                    source_id=source.source_id,
                                    pub_model=pub,
                                    cites_chameleon_pub=None,
                                    found_with_query=None,
                                ),
                            )
                        pub.delete()
                        duplicates_count += 1
                    else:
                        new_pubs_count += 1

                messages.success(
                    request,
                    f"Added {new_pubs_count} new publications. Merged {duplicates_count} duplicate(s).",
                )

                return redirect(request.path)
            else:
                messages.error(request, "Error adding publication(s).")
                for error in form.bibtex_errors:
                    messages.error(request, error)
                form.bibtex_errors = []

        else:
            form = AddBibtexPublicationForm(
                is_admin=True,
                initial={"project_id": "admin", "confirmation": "confirmed"},
            )

        extra_context["add_bibtex_form"] = form

        return super().changelist_view(request, extra_context=extra_context)

    def source_count(self, obj):
        return RawPublication.objects.filter(publication=obj).count()

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

    def potential_project(self, obj):
        def _project_href(proj):
            return f'<a href="/user/projects/{proj.pk}" target="_blank">{proj.charge_code}</a>'

        if obj.project:
            return mark_safe(f"submitted by {_project_href(obj.project)}")

        authors = [author.strip() for author in obj.author.split("and")]
        projects = PublicationUtils.get_projects_for_author_names(authors, obj.year)

        # Get valid projects that are active prior to the publication year
        valid_projects = []
        for project_code in projects:
            try:
                project = Project.objects.get(charge_code=project_code)
            except Project.DoesNotExist:
                LOG.info(f"{project_code} does not exist in database")
                continue
            if not obj.year or utils.is_project_prior_to_publication(project, obj.year):
                valid_projects.append(f"<li>{_project_href(project)}</li>")

        return mark_safe("<ul>" + "".join(valid_projects) + "</ul>")

    def _to_html_list(self, items):
        markup = []
        for item in items:
            markup.append(f"<li>{item}</li>")
        return mark_safe("<ul>" + "".join(markup) + "</ul>")

    def source_comparison(self, obj):
        sources = RawPublication.objects.filter(publication=obj)
        titles = {source.title for source in sources}
        forums = {source.forum for source in sources}
        publication_types = {source.publication_type for source in sources}
        authors = {source.author for source in sources}
        all_props = [
            f"<h3>Titles</h3><div>{self._to_html_list(titles)}</div>",
            f"<h3>Forums</h3><div>{self._to_html_list(forums)}</div>",
            f"<h3>Types</h3><div>{self._to_html_list(publication_types)}</div>",
            f"<h3>Authors</h3><div>{self._to_html_list(authors)}</div>",
        ]
        return self._to_html_list(all_props)

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

        RawPublication.objects.filter(publication=duplicate).update(
            publication=original
        )
        duplicate.delete()

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
        super().save_model(request, obj, form, change)


class ForumAliasInline(admin.TabularInline):
    model = ForumAlias
    extra = 1


class ForumPublicationInline(admin.TabularInline):
    model = Publication
    extra = 0
    fields = ["title", "author"]
    can_delete = False
    fk_name = "normalized_forum"
    show_change_link = True

    def has_change_permission(self, request, obj=None):
        return False


class ForumAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "pub_count",
        "organization",
        "forum_type",
        "country",
        "source",
    )
    search_fields = ("name", "organization", "forum_type", "country")
    inlines = [ForumAliasInline, ForumPublicationInline]
    readonly_fields = ["pub_count"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(pub_count=Count("publications"))

    def pub_count(self, obj):
        return obj.pub_count

    pub_count.admin_order_field = "pub_count"
    pub_count.short_description = "Publications"


admin.site.register(Publication, PublicationAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ChameleonPublication, ChameleonPublicationAdmin)
# admin.site.register(PublicationSource, PublicationSourceAdmin)
admin.site.register(RawPublication, RawPublicationAdmin)
admin.site.register(PublicationQuery, PublicationQueryAdmin)
admin.site.register(Forum, ForumAdmin)
