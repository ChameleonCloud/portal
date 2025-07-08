import datetime
import logging

import bibtexparser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Max
from django.http import Http404
from django.template.loader import get_template
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from djangoRT import rtModels, rtUtil
from projects.models import Publication, PublicationSource, Project
from projects.user_publication.deduplicate import get_duplicate_pubs
from projects.util import get_project_members
from projects.views import project_member_or_admin_or_superuser
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
    pubs = Publication.objects.filter(project_id__in=project_ids).exclude(
        status=Publication.STATUS_DELETED
    )
    for pub in pubs:
        project = ProjectAllocationMapper.get_publication_project(pub)
        if project:
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
                        else datetime.datetime.strptime(str(pub.month), "%m").strftime(
                            "%b"
                        )
                    ),
                    "year": pub.year,
                    "nickname": project.nickname,
                    "chargeCode": project.charge_code,
                    "status": pub.status,
                    "added_by_username": pub.added_by_username,
                    "submitted_date": pub.submitted_date,
                    "reviewed_by": pub.reviewed_by,
                    "reviewed_date": pub.reviewed_date,
                    "reviewed_comment": pub.reviewed_comment,
                }
            )
    logger.info(get_template("projects/view_publications.html").template.origin)
    return render(request, "projects/view_publications.html", context)


@login_required
def add_publications(request, project_id):
    mapper = ProjectAllocationMapper(request)
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
        pubs_form = AddBibtexPublicationForm(request.POST)
        if pubs_form.is_valid():
            bib_database = bibtexparser.loads(pubs_form.cleaned_data["bibtex_string"])
            new_pubs = []
            with transaction.atomic():
                for entry in bib_database.entries:
                    new_pub = Publication.objects.create_from_bibtex(
                        entry,
                        project,
                        request.user.username,
                        "user_reported",
                        Publication.STATUS_SUBMITTED,
                    )
                    pub_source = PublicationSource(publication=new_pub)
                    pub_source.name = PublicationSource.USER_REPORTED
                    pub_source.save()
                    new_pubs.append(new_pub)
            messages.success(request, "Publication(s) added successfully")
            ticket_id = _send_publication_notification(project.chargeCode, new_pubs)
            duplicate_pubs = get_duplicate_pubs(new_pubs)
            # if any of the pubs have duplicates
            if any(v for v in duplicate_pubs.values()):
                _send_duplicate_pubs_notification(
                    ticket_id, project.chargeCode, duplicate_pubs
                )
        else:
            messages.error(request, "Error adding publication(s).")
            for error in pubs_form.bibtex_errors:
                messages.error(request, error)
            pubs_form.bibtex_errors = []

    pubs_form = AddBibtexPublicationForm(initial={"project_id": project.id})

    return render(
        request,
        "projects/add_publications.html",
        {
            "project": project,
            "project_nickname": project.nickname,
            "is_pi": request.user.username == project.pi.username,
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
