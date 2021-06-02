from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .forms import AddBibtexPublicationForm
from django.contrib import messages
from projects.views import project_pi_or_admin_or_superuser
from projects.models import Publication
from util.project_allocation_mapper import ProjectAllocationMapper
import logging
import bibtexparser
import datetime

logger = logging.getLogger("projects")


@login_required
def user_publications(request):
    context = {}
    if "del_pub" in request.POST:
        try:
            del_pub_id = request.POST["pub_ref"]
            logger.debug("deleting publication with id {}".format(del_pub_id))
            Publication.objects.get(pk=del_pub_id).delete()
        except Exception:
            logger.exception("Failed removing publication")
            messages.error(
                request,
                "An unexpected error occurred while attempting "
                "to remove this publication. Please try again",
            )
    context["publications"] = []
    pubs = Publication.objects.filter(added_by_username=request.user.username)
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
                    "month": ""
                    if not pub.month
                    else datetime.datetime.strptime(str(pub.month), "%m").strftime(
                        "%b"
                    ),
                    "year": pub.year,
                    "nickname": project.nickname,
                    "chargeCode": project.charge_code,
                }
            )
    return render(request, "projects/view_publications.html", context)


@login_required
def add_publications(request, project_id):
    mapper = ProjectAllocationMapper(request)
    try:
        project = mapper.get_project(project_id)
        if project.source != "Chameleon" or not project_pi_or_admin_or_superuser(
            request.user, project
        ):
            raise Http404("The requested project does not exist!")
    except Exception as e:
        logger.error(e)
        raise Http404("The requested project does not exist!")
    if request.POST:
        pubs_form = AddBibtexPublicationForm(request.POST)
        if pubs_form.is_valid():
            bib_database = bibtexparser.loads(pubs_form.cleaned_data["bibtex_string"])
            for entry in bib_database.entries:
                Publication.objects.create_from_bibtex(
                    entry, project, request.user.username
                )
            messages.success(request, "Publication added successfully")
        else:
            messages.error(request, "Error adding publication")
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
