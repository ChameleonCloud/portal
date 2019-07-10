import django_filters

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.template import context
from django.views import generic

from .models import Artifact, Author
#from . import filters

from django.shortcuts import render

### Active Views ###
class IndexView(generic.ListView):
    template_name = 'sharing/index.html'
    context_object_name = 'artifacts'
    def get_queryset(self):
        return Artifact.objects.order_by('-created_at')

class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter() #pub_date__lte=timezone.now)


### Filtering Attempts ###
'''
def artifact_list(request):
    f = LabelFilter(request.GET, queryset=Artifact.objects.all())
    return render(request, 'sharing/index.html', {'filter': f})

class FilterView(generic.FilterView):
    model = Artifact
    template_name = 'sharing/index.html'
    filterset_class=LabelFilter
    context_object_name = 'artifacts'
    def get_queryset(self):
        return Artifact.objects.order_by('-created_at')

'''
