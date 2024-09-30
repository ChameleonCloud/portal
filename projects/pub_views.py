import datetime
import logging

import bibtexparser
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import render
from django.utils.html import strip_tags
from django.core.exceptions import PermissionDenied

from projects.models import Publication, PublicationSource
from projects.user_publication.deduplicate import get_duplicate_pubs
from projects.util import get_project_members
from projects.views import project_member_or_admin_or_superuser
from util.project_allocation_mapper import ProjectAllocationMapper

from .forms import AddBibtexPublicationForm

logger = logging.getLogger("projects")


def _send_publication_notification(charge_code, pubs):
    subject = f"Project {charge_code} added new publications"
    formatted_pubs = [f"<li>{pub.__repr__()}<br><br></li>" for pub in pubs]
    body = f"""
    <p>Please review the following publications added by
    project {charge_code}:
    <ul>{" ".join(formatted_pubs)}</ul>
    </p>
    """
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.PENDING_ALLOCATION_NOTIFICATION_EMAIL],
        message=strip_tags(body),
        html_message=body,
    )


def _send_duplicate_pubs_notification(charge_code, duplicate_pubs):
    subject = "Project {charge_code} plausible duplicate uploaded"
    formatted_duplicate_pubs = [
        (
            f"<li>{pub.__repr__()} <br>Found duplicate for <br>"
            f"{duplicate_pubs[pub]} <br><br></li>"
        ).replace("\n", "<br>")
        for pub in duplicate_pubs
    ]
    formatted_duplicate_pubs = formatted_duplicate_pubs
    body = f"""
    <p>Please review the following publications which are plausible duplicates by
    project {charge_code}:
    <ul>{" ".join(formatted_duplicate_pubs)}</ul>
    </p>
    """
    send_mail(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.PENDING_ALLOCATION_NOTIFICATION_EMAIL],
        message=strip_tags(body),
        html_message=body,
    )


@login_required
def user_publications(request):
    context = {}
    if "del_pub" in request.POST:
        try:
            del_pub_id = request.POST["pub_ref"]
            logger.debug("deleting publication with id {}".format(del_pub_id))
            Publication.objects.get(pk=del_pub_id).delete_pub()
        except Exception:
            logger.exception("Failed removing publication")
            messages.error(
                request,
                "An unexpected error occurred while attempting "
                "to remove this publication. Please try again",
            )
    context["publications"] = []
    pubs = Publication.objects.filter(added_by_username=request.user.username).exclude(
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
                }
            )
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
            _send_publication_notification(project.chargeCode, new_pubs)
            duplicate_pubs = get_duplicate_pubs(new_pubs)
            # if any of the pubs have duplicates
            if any(v for v in duplicate_pubs.values()):
                _send_duplicate_pubs_notification(project.chargeCode, duplicate_pubs)
        else:
            messages.error(
                request, f"Error adding publication(s). {pubs_form.bibtex_error}"
            )
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
    pubs = (
        Publication.objects.filter(
            checked_for_duplicates=True, status=Publication.STATUS_APPROVED
        )
        .order_by("-year", "title")
        .annotate(max_cites_from_all_sources=Max("sources__citation_count"))
    )
    return render(
        request,
        "projects/chameleon_used_in_research.html",
        {"pubs": pubs},
    )
