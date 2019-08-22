from datetime import datetime
import json
from urllib.request import urlopen, Request

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.views import generic

from .models import Artifact, Author, Label
from .forms import LabelForm, UploadForm
from .__init__ import DEV as dev


def artifacts_from_form(data):
    """Return a filtered artifact list from search form data
    
    Parameters
    ----------
    data : dict
        Expected to be of the form:
        {
            'labels': list of ints,
            'search': string,
            'is_or': bool,
        }

    Returns
    -------
    list of Artifacts
        Filtered based on search parameters
    """

    chosen_labels = data.get('labels', [])
    keywords = data.get('search', '')
    is_or = data.get('is_or', False)

    # Start with the full list of artifacts
    filtered = Artifact.objects.all()

    # Filter by those containing the specified keywords
    if keywords:
        filtered = filtered.filter(
            Q(title__contains=keywords) |
            Q(description__contains=keywords) |
            Q(short_description__contains=keywords) |
            Q(authors__full_name__contains=keywords)
        )

    # Then, look at the labels
    if chosen_labels == []:
        # If there are no specified lables, include them all
        filtered = filtered
    elif is_or:
        # If you chose 'or', include all artifacts
        # with any of the specified labels
        filtered = filtered.filter(labels__in=chosen_labels)
    else:
        # Otherwise, only include artifacts with all chosen labels
        for label in chosen_labels:
            filtered = filtered.filter(labels__exact=label)

    # Don't list any artifact twice in the returned list
    return filtered.distinct()


def make_author(name_string):
    """Return a filtered artifact list from search form data
    
    Parameters
    ----------
    name_string : string
        Name to be parsed

    Returns
    -------
    int
        Primary key (id) of created author
    """

    # Split name into parts by spaces
    name = name_string.split(' ')

    # Initalize title and last name to be empty
    title = ''
    lname = ''

    length = len(name)
    # If there are more than three parts, we don't know how to parse
    # So, put the whole name as the first name
    if length > 3:
        fname = name_string

    # If there are three parts, look at the first
    elif length == 3:
        # If part 1 has a '.' it's probably a title (Mr., Dr., etc)
        if '.' in name[0]:
            title = name[0]
            fname = name[1]
        # If not, group it with the first name
        else:
            fname = name[0]+' '+name[1]
        # The last part is the last name
        lname = name[2]
    # If there are two parts, parse as firstname lastname
    elif length == 2:
        fname = name[0]
        lname = name[1]
    # If there's only one part, call it the first name
    else:
        fname = name[0]

    # Create an 'Author' based on the parsed elements (some may be blank)
    author = Author(
        title=title,
        first_name=fname,
        last_name=lname
    )
    # Save the author
    author.save()

    # Return the author's id
    return author.pk


def upload_artifact(data, doi):
    # TODO: use helper
    zparts = doi.split('.')
    record_id = zparts[len(zparts)-1]

    if dev:
        api = "https://sandbox.zenodo.org/api/records/"
    else:
        api = "https://zenodo.org/api/records/"
    req = Request(
        "{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )
    try:
        resp = urlopen(req)
    except Exception as e:
        return
    record = json.loads(resp.read().decode("utf-8"))

    item = Artifact(
        title=record['metadata']['title'],
        description=record['metadata']['description'],
        # short_description = data['short_description'],
        # image = data['image'],
        # git_repo = data['git_repo'],
        doi=doi,
        launchable=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    item.save()
    # item.associated_artifacts.set(data['associated_artifacts'])
    # item.labels.set(data['labels'])
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
            except Exception:
                context['artifacts'] = []
                context['search_failed'] = True
            return HttpResponse(template.render(context, request))
    else:
        form = LabelForm()
        context['form'] = form
        context['submitted'] = 'no'
        context['artifacts'] = Artifact.objects.all()
        return HttpResponse(template.render(context, request))


def upload(request):
    context = {}
    doi = request.GET.get('doi')
    if doi is None:
        context['error'] = True
        context['error_message'] = "No doi was provided"
        return HttpResponseRedirect('/portal/')
    print("doi: "+doi)

    template = loader.get_template('sharing/upload.html')

    form = UploadForm(request.POST)
    if form.is_valid():
        pk = upload_artifact(form.cleaned_data, doi)
        if pk is None:
            error_message = "There is no Zenodo publication with that DOI"
            messages.add_message(request, messages.INFO, error_message)
            context['error'] = True
            context['error_message'] = error_message
            return HttpResponseRedirect('/portal/')
        else:
            context['form'] = form
            return HttpResponseRedirect('/portal/'+str(pk))
    else:
        return HttpResponse(template.render(context, request))


class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter()
