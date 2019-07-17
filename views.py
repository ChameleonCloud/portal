from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from django.views import generic
from .models import Artifact, Author, Label

from .forms import LabelForm, UploadForm

def artifacts_from_form(data):
    chosen_labels = data['labels']
    keywords = data['search']

    filtered = Artifact.objects.all() 
    if keywords is not None:
        filtered=filtered.filter(
            Q(title__contains=keywords) |
            Q(description__contains=keywords) |
            Q(short_description__contains=keywords) |
            Q(authors__full_name__contains=keywords)
        )
    if chosen_labels == []:
        filtered = filtered
    elif data['is_or']:
        filtered = filtered.filter(labels__in=chosen_labels)
    else:
        for label in chosen_labels:
            filtered = filtered.filter(labels__exact=label)
    return filtered.distinct()

def upload_artifact(data,doi):
    item = Artifact(
        title=data['title'],
        short_description = data['short_description'],
        description = data['description'],
        image = data['image'],
        doi = doi,
        git_repo = data['git_repo'],
        launchable = data['launchable'],
        created_at = data['created_at'],
        updated_at = data['updated_at'],
    )
    item.save()
    item.associated_artifacts.set(data['associated_artifacts'])
    item.labels.set(data['labels'])
    item.authors.set(data['authors'])
    item.save()
    return item.pk


def index(request):
    template = loader.get_template('sharing/index.html')
    context = {}

    if request.method == 'POST':
        form = LabelForm(request.POST)
        if form.is_valid():
            chosen_labels = form.cleaned_data['labels'] 
            context['form'] = form
            context['submitted'] = chosen_labels
            context['searched'] = form.cleaned_data['search']
            try:
                context['artifacts'] = artifacts_from_form(form.cleaned_data)
                context['search_failed'] = False
            except:
                context['artifacts'] = []
                context['search_failed'] = True
            return HttpResponse(template.render(context,request))
    else:
        form=LabelForm()
        context['form'] = form
        context['submitted'] = 'no'
        context['artifacts'] = Artifact.objects.all()
        return HttpResponse(template.render(context,request))

def upload(request, doi):
    template = loader.get_template('sharing/upload.html')
    context = {}

    if request.method == 'POST':
        form = UploadForm(request.POST)
        if form.is_valid():
            pk = upload_artifact(form.cleaned_data,doi)
            context['form'] = form
            print("form was valid")
            return HttpResponseRedirect('/portal/'+str(pk))
        else:
            return HttpResponse(template.render(context,request))
    else:
        form=UploadForm()
        context['form'] = form
        return HttpResponse(template.render(context,request))


class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter()

