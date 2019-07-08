from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from .models import Artifact, Author

from django.shortcuts import render

# Create your views here.
class IndexView(generic.ListView):
    template_name = 'sharing/index.html'
    context_object_name = 'artifacts'
    def get_queryset(self):
        return Artifact.objects.order_by('-created_at')
#    return HttpResponse("This is the sharing portal index")

class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter() #pub_date__lte=timezone.now)

