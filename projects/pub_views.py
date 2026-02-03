import datetime
import logging

import bibtexparser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404
from django.template.loader import get_template
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
import json
import pydetex.pipelines as pip

from djangoRT import rtModels, rtUtil
from projects.models import (
    ChameleonPublication,
    Publication,
    PublicationQuery,
    RawPublication,
)
from projects.user_publication.deduplicate import get_duplicate_pubs
from projects.user_publication.utils import PublicationUtils, update_cites_and_query
from projects.util import get_project_members
from projects.views import is_pi_eligible, project_member_or_admin_or_superuser
from util.project_allocation_mapper import ProjectAllocationMapper

# from chameleon.research_impacts import get_education_users

from .forms import AddBibtexPublicationForm

logger = logging.getLogger("projects")


def _send_publication_notification(charge_code, pubs):
    """Create ticket to notifiy of new publication

    Returns: the new ticket id
    """
    subject = f"Project {charge_code} added new publications"
    formatted_pubs = "\n".join([f"- {pub.__repr__()}" for pub in pubs])
    body = f"""Please review the following publications added by project {charge_code}:
    {formatted_pubs}
    """
    rt = rtUtil.DjangoRt()
    ticket = rtModels.Ticket(
        subject=subject,
        problem_description=body,
        requestor="us@tacc.utexas.edu",
    )
    ticket_id = rt.createTicket(ticket)
    for pub in pubs:
        pub.ticket_id = ticket_id
        pub.save()


def _send_duplicate_pubs_notification(ticket_id, charge_code, duplicate_pubs):
    formatted_duplicate_pubs = "\n".join(
        [
            (f"- {pub.__repr__()}: Found duplicate for {duplicate_pubs[pub]}").replace(
                "\n", ""
            )
            for pub in duplicate_pubs
        ]
    )
    formatted_duplicate_pubs = formatted_duplicate_pubs
    body = f"""Please review the following publications which are plausible duplicates by project {charge_code}:
    {formatted_duplicate_pubs}
    """
    rt = rtUtil.DjangoRt()
    rt.replyToTicket(ticket_id, text=body)


@login_required
def user_publications(request):
    context = {}
    if "del_pub" in request.POST:
        try:
            del_pub_id = request.POST["pub_ref"]
            logger.debug("deleting publication with id {}".format(del_pub_id))
            pub = Publication.objects.get(pk=del_pub_id)
            if pub.added_by_username != request.user.username:
                messages.error(
                    request,
                    "You do not have permission to delete that publication!",
                )
            else:
                pub.delete_pub()
        except Exception:
            logger.exception("Failed removing publication")
            messages.error(
                request,
                "An unexpected error occurred while attempting "
                "to remove this publication. Please try again",
            )
    mapper = ProjectAllocationMapper(request)
    project_ids = [p["id"] for p in mapper.get_user_projects(request.user.username)]
    context["publications"] = []
    pubs = (
        Publication.objects.filter(
            Q(project_id__in=project_ids) | Q(added_by_username=request.user.username)
        )
        .exclude(status=Publication.STATUS_DELETED)
        .exclude(status="DUPLICATE")
    )
    nice_status_map = {
        Publication.STATUS_SUBMITTED: "Pending Review",
        Publication.STATUS_APPROVED: "Verified",
    }
    for pub in pubs:
        nice_status = nice_status_map.get(pub.status, None)
        if not nice_status:
            nice_status = pub.get_status_display()

        context["publications"].append(
            {
                "id": pub.id,
                "title": pub.title,
                "author": pub.author,
                "link": "" if not pub.link else pub.link,
                "forum": pub.forum,
                "month": (
                    ""
                    if not pub.month
                    else datetime.datetime.strptime(str(pub.month), "%m").strftime("%b")
                ),
                "year": pub.year,
                "status": pub.status,
                "nice_status": nice_status,
                "added_by_username": pub.added_by_username,
                "reviewed_by": pub.reviewed_by,
                "reviewed_date": pub.reviewed_date,
                "reviewed_comment": pub.reviewed_comment,
            }
        )
    context["is_pi"] = is_pi_eligible(request.user)
    logger.info(get_template("projects/view_publications.html").template.origin)
    return render(request, "projects/view_publications.html", context)


def entry_to_id(entry: dict) -> str:
    """
    Generate a normalized source_id from entry title, author, journal, and year.
    Ensures the string fits within 1024 characters.
    """
    title = entry.get("title", "").strip().lower()
    author = entry.get("author", "").strip().lower()
    journal = entry.get("journal", "").strip().lower()
    year = entry.get("year", "").strip()
    key = f"{year}|{author}|{journal}|{title}"

    if len(key) > 1024:
        key = key[:1024]
    return key


def create_pub_from_bibtex(bibtex_entry, project, username, status):
    pub = Publication()

    if project:
        pub.project_id = project.id

    pub.publication_type = PublicationUtils.get_pub_type(bibtex_entry)
    pub.title = pip.strict(bibtex_entry.get("title", ""))
    pub.year = bibtex_entry.get("year")
    pub.month = PublicationUtils.get_month(bibtex_entry)
    pub.author = pip.strict(bibtex_entry.get("author", ""))
    pub.bibtex_source = json.dumps(bibtex_entry)
    pub.added_by_username = username
    pub.forum = PublicationUtils.get_forum(bibtex_entry)
    pub.link = PublicationUtils.get_link(bibtex_entry)
    pub.doi = bibtex_entry.get("doi")
    pub.status = status

    pub.save()
    return pub


def create_pubs_from_bibtext_string(
    str,
    project,
    username,
    source="user_reported",
    cites_chameleon_pub_id=None,
    found_with_query_id=None,
):
    bib_database = bibtexparser.loads(str)
    new_pubs = []
    with transaction.atomic():
        for entry in bib_database.entries:
            logger.info(entry)
            source_id = entry_to_id(entry)

            new_pub = create_pub_from_bibtex(
                entry,
                project,
                username,
                Publication.STATUS_SUBMITTED,
            )

            cites_chameleon_pub = None
            if cites_chameleon_pub_id:
                try:
                    cites_chameleon_pub = ChameleonPublication.objects.get(
                        id=cites_chameleon_pub_id
                    )
                except ChameleonPublication.DoesNotExist:
                    pass
            found_with_query = None
            if found_with_query_id:
                try:
                    found_with_query = PublicationQuery.objects.get(
                        id=found_with_query_id
                    )
                except PublicationQuery.DoesNotExist:
                    pass

            if source == "user_reported":
                pub_source = RawPublication.from_publication(
                    new_pub, RawPublication.USER_REPORTED
                )
                pub_source.save()
            elif source == "google_scholar":
                # Check if we already have this source
                pub_source = RawPublication.objects.filter(
                    source_id=source_id, name=source
                ).first()
                if not pub_source:
                    pub_source = RawPublication.from_publication(
                        new_pub, RawPublication.GOOGLE_SCHOLAR
                    )
                    pub_source.source_id = source_id
                    pub_source.save()
                    update_cites_and_query(
                        pub_source, cites_chameleon_pub, found_with_query
                    )
                else:
                    update_cites_and_query(
                        pub_source, cites_chameleon_pub, found_with_query
                    )
                    # update the links, but undi the pub creation here
                    new_pub.delete()
                    continue
            new_pubs.append(new_pub)
    return new_pubs


@login_required
@login_required
def add_publications(request, project_id=None):
    mapper = ProjectAllocationMapper(request)

    project = None
    users = []

    # Only try to load a project if project_id was provided
    if project_id:
        try:
            project = mapper.get_project(project_id)
            if project.source != "Chameleon":
                raise Http404("The requested project does not exist!")
        except Exception as e:
            logger.error(e)
            raise Http404("The requested project does not exist!")

        users = get_project_members(project)
        if not project_member_or_admin_or_superuser(request.user, project, users):
            raise PermissionDenied

    if request.POST:
        pubs_form = AddBibtexPublicationForm(request.POST, user=request.user)
        if pubs_form.is_valid():
            # If project not in url, load it from form
            if pubs_form.cleaned_data["project_id"]:
                project = project or mapper.get_project(
                    pubs_form.cleaned_data["project_id"]
                )

            new_pubs = create_pubs_from_bibtext_string(
                pubs_form.cleaned_data["bibtex_string"],
                project,
                request.user.username,
            )
            messages.success(request, "Publication(s) added successfully")
            if project:
                _send_publication_notification(project.chargeCode, new_pubs)
            else:
                _send_publication_notification("unspecified", new_pubs)
        else:
            messages.error(request, "Error adding publication(s).")
            for error in pubs_form.errors:
                messages.error(request, error)
            for error in pubs_form.bibtex_errors:
                messages.error(request, error)
            pubs_form.bibtex_errors = []

    initial = {"project_id": project.id} if project else {}
    pubs_form = AddBibtexPublicationForm(initial=initial, user=request.user)

    return render(
        request,
        "projects/add_publications.html",
        {
            "project": project,
            "project_nickname": project.nickname if project else "",
            "pubs_form": pubs_form,
            "form": pubs_form,
        },
    )


def view_chameleon_used_in_research_publications(request):
    # Get all approved publications
    pubs = (
        Publication.objects.filter(
            checked_for_duplicates=True, status=Publication.STATUS_APPROVED
        )
        .order_by("-year", "title")
        .annotate(max_cites_from_all_sources=Max("sources__citation_count"))
    )

    # Calculate research impact statistics
    impact_stats = {}

    # Total number of publications
    total_pubs = pubs.count()
    impact_stats["total_publications"] = total_pubs
    # For aggregations
    pub_query = Publication.objects.filter(
        checked_for_duplicates=True, status=Publication.STATUS_APPROVED
    )

    last_reviewed = pub_query.aggregate(Max("reviewed_date"))["reviewed_date__max"]
    if last_reviewed:
        last_reviewed = last_reviewed.strftime("%Y-%m-%d")
    else:
        last_reviewed = "N/A"
    impact_stats["last_reviewed"] = last_reviewed

    # Publications by year (last 5 years)
    # current_year = timezone.now().year
    # years_range = list(range(current_year - 4, current_year + 1))

    # pubs_by_year = list(
    #     pub_query.values("year")
    #     .annotate(count=models.Count("id"))
    #     .filter(year__in=years_range)
    #     .order_by("year")
    # )

    # Create a complete dataset with all years, filling in zeros for missing years
    # complete_pubs_by_year = []
    # year_counts = {item["year"]: item["count"] for item in pubs_by_year}
    # for year in years_range:
    #     complete_pubs_by_year.append({"year": year, "count": year_counts.get(year, 0)})
    # impact_stats["publications_by_year"] = complete_pubs_by_year

    # Active projects (with allocations that are active or approved) TODO Move active project statistics to another view
    # active_projects = (
    #     Project.objects.filter(allocations__status__in=["active", "approved"])
    #     .distinct()
    #     .count()
    # )
    # impact_stats["active_projects"] = active_projects

    # Historical projects (projects that have ever had an approved allocation)
    # historical_projects = (
    #     Project.objects.filter(
    #         allocations__status__in=["active", "approved", "inactive"]
    #     )
    #     .distinct()
    #     .count()
    # )
    # impact_stats["historical_projects"] = historical_projects

    # Publication types distribution (top 5)
    # TODO Need to clean up data quality issues in the publication_type field
    # pub_types = list(
    #     pub_query.values("publication_type")
    #     .annotate(count=models.Count("id"))
    #     .order_by("-count")[:5]
    # )
    # impact_stats["publication_types"] = pub_types

    return render(
        request,
        "projects/chameleon_used_in_research.html",
        {
            "pubs": pubs,
            "impact_stats": impact_stats,
        },
    )
