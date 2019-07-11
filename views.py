from django.http import HttpResponse
from django.template import loader

from django.views import generic
from .models import Artifact, Author, Label

from .forms import LabelForm

def index(request):
    template = loader.get_template('sharing/index.html')
    context = {}

    if request.method == 'POST':
        form = LabelForm(request.POST)
        if form.is_valid():
            chosen_labels = form.cleaned_data['labels'] 
            context['form'] = form
            context['submitted'] = chosen_labels
            filtered_set = Artifact.objects.filter(labels__in=chosen_labels)

            context['artifacts'] = filtered_set
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
