from django.db.models import Q
from django.http import HttpResponse
from django.template import loader

from django.views import generic
from .models import Artifact, Author, Label

from .forms import LabelForm

def artifacts_from_form(data):
    chosen_labels = data['labels']
    if chosen_labels == []:
        filtered = Artifact.objects.all() 
    elif data['is_or']:
        filtered = Artifact.objects.filter(labels__in=chosen_labels)
    else:
        
            
        q = Q()
        for label in chosen_labels:
            q &= Q(labels__in=label)
        filtered = Artifact.objects.get(q)
#        filtered = Artifact.objects.filter(labels__in=chosen_labels)
    return filtered

def index(request):
    template = loader.get_template('sharing/index.html')
    context = {}

    if request.method == 'POST':
        form = LabelForm(request.POST)
        if form.is_valid():
            chosen_labels = form.cleaned_data['labels'] 
            context['form'] = form
            context['submitted'] = chosen_labels
#            context['artifacts'] = Artifact.objects.filter(labels=chosen_labels)
            context['artifacts'] = artifacts_from_form(form.cleaned_data)
            return HttpResponse(template.render(context,request))
    else:
        form=LabelForm()
        context['form'] = form
        context['submitted'] = 'no'
        context['artifacts'] = Artifact.objects.all()
        return HttpResponse(template.render(context,request))


class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter()
