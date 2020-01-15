from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from forms import AddBibtexPublicationForm

from projects.views import get_projects



@login_required
def user_publications(request):
    context = {}

    context['publications'] = {}

    return render(request, 'publications/view_publications.html', context)

@login_required
def add_publications(request):
    context = {}
    projects = get_projects(request)
    ALLOCATIONS_LIST = []
    for p in projects:
        ALLOCATIONS_LIST.append((str(p.chargeCode), str(p.chargeCode)))
    form = AddBibtexPublicationForm(ALLOCATIONS_LIST=ALLOCATIONS_LIST)
    context['form'] = form
    context['publications'] = {}

    return render(request, 'publications/add_publications.html', context)
