from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from forms import AddBibtexPublicationForm

from projects.views import get_projects

from projects.models import Publication, ProjectExtras


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


    return render(request, 'publications/view_publications.html', context)

@login_required
def add_publications(request):
    context = {}
    projects = get_projects(request)
    # ALLOCATIONS_LIST = []
    # for p in projects:
    #     ALLOCATIONS_LIST.append((str(p.chargeCode), str(p.chargeCode)))
    # form = AddBibtexPublicationForm(ALLOCATIONS_LIST=ALLOCATIONS_LIST)
    form = AddBibtexPublicationForm()
    context['form'] = form
    context['publications'] = {}

    return render(request, 'publications/add_publications.html', context)
