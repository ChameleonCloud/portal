import json 

from datetime import datetime
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from django.views import generic
from .models import Artifact, Author, Label

from urllib.request import urlopen, Request
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


def make_author(name_string):
    name = name_string.split(' ')
    length = len(name)
    title=''
    if length > 3:
        fname = name_string
    elif length == 3:
        if '.' in name[0]:
            title=name[0]
            fname=name[1]
        else:
            fname=name[0]+' '+name[1]
        lname = name[2]
    elif length==2:
        fname = name[0]
        lname = name[1]
    else: 
        fname = name[0]
    author = Author(
        title=title,
        first_name = fname,
        last_name = lname
    )
    author.save()
    return author.pk
            

def upload_artifact(data,doi):

    zparts = doi.split('.')
    record_id = zparts[len(zparts)-1]
    api = "https://zenodo.org/api/records/"
    req = Request(
        "{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )
    resp = urlopen(req)
    record = json.loads(resp.read().decode("utf-8"))

    item = Artifact(
        title=record['metadata']['title'],
        description = record['metadata']['description'],

        short_description = data['short_description'],
        image = data['image'],
        git_repo = data['git_repo'],

        doi = doi,
        launchable = True,
        created_at = datetime.now(),
        updated_at = datetime.now(),
    )
    item.save()
    item.associated_artifacts.set(data['associated_artifacts'])
    item.labels.set(data['labels'])
    author_list = []
    for author in record['metadata']['creators']:
        name = author['name']  
        author_list.append(make_author(name))
    item.authors.set(author_list)
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

