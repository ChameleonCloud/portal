from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import (Http404, HttpResponseForbidden, HttpResponse,
                         HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse)
from forms import AddBibtexPublicationForm
from django.contrib import messages
from projects.views import get_projects, project_pi_or_admin_or_superuser
from projects.models import Publication, ProjectExtras
from pytas.models import Project
import logging
import bibtexparser
logger = logging.getLogger('projects')

@login_required
def user_publications(request):
    context = {}
    context['publications'] = []
    pubs = Publication.objects.filter(added_by_username=request.user.username)
    for pub in pubs:
        pextras = ProjectExtras.objects.filter(tas_project_id=pub.tas_project_id)
        nickname = None
        if pextras.count > 0:
            nickname = pextras[0].nickname
        context['publications'].append({'title':pub.title, 'author':pub.author, 'abstract':pub.abstract, \
            'nickname': nickname, 'chargeCode': pub.tas_project_id})
    return render(request, 'projects/view_publications.html', context)

@login_required
def add_publications(request, project_id):
    try:
        project = Project(project_id)
        if project.source != 'Chameleon' or not \
            project_pi_or_admin_or_superuser(request.user, project):
            raise Http404('The requested project does not exist!')
    except Exception as e:
        logger.error(e)
        raise Http404('The requested project does not exist!')
    if request.POST:
        pubs_form = AddBibtexPublicationForm(request.POST)
        if pubs_form.is_valid():
            bib_database = bibtexparser.loads(pubs_form.cleaned_data['bibtex_string'])
            for entry in bib_database.entries:
                Publication.objects.create_from_bibtex(entry, project, request.user.username)
            messages.success(request, 'Publication added successfully')
        else:
            messages.error(request, 'Error adding publication, BibTeX required fields: "publication/journal/booktitle, title, year, author"')
    try:
        project = Project(project_id)
        if project.source != 'Chameleon':
            raise Http404('The requested project does not exist!')
    except Exception as e:
        logger.error(e)
        raise Http404('The requested project does not exist!')
    pubs_form = AddBibtexPublicationForm(initial={'project_id':project.id})
    try:
        extras = ProjectExtras.objects.get(tas_project_id=project_id)
        project_nickname = extras.nickname
    except ProjectExtras.DoesNotExist:
        project_nickname = None

    return render(request, 'projects/add_publications.html', {
        'project': project,
        'project_nickname': project_nickname,
        'is_pi': request.user.username == project.pi.username,
        'pubs_form': pubs_form,
        'form': pubs_form
    })
