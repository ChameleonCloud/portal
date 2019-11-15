from datetime import datetime
import logging
import json
from urllib.request import urlopen, Request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.views import generic

from .conf import JUPYTERHUB_URL, ZENODO_SANDBOX
from .forms import ArtifactForm, LabelForm
from .models import Artifact, ArtifactVersion, Author, Label
from .zenodo import ZenodoClient

LOG = logging.getLogger(__name__)

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

    chosen_labels = data.get('labels') or []
    keywords = data.get('search') or ''
    is_or = data.get('is_or') or False

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
    # Initalize title and last name to be empty
    title = ''
    lname = ''

    # Split name into parts by spaces and commas
    name = name_string.split(' ')
    length = len(name)
    comma_split = name_string.split(',')

    # If there's a comma, assume the form lname, fname
    if len(comma_split) == 2:
        lname = comma_split[0].strip()
        fname = comma_split[1].strip()
    # If there are more than three parts, we don't know how to parse
    # So, put the whole name as the first name
    elif length > 3:
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


def upload_artifact(doi, user=None):
    """ Add item to the portal based on its Zenodo deposition

    Parameters
    ----------
    doi : string
        DOI of deposition to upload

    Returns
    -------
    int or None
        pk of successful upload on success, None on failure
    """
    # Extract the record id
    record_id = ZenodoClient.to_record(doi)

    # Use the appropriate api base
    if ZENODO_SANDBOX:
        api = "https://sandbox.zenodo.org/api/records/"
    else:
        api = "https://zenodo.org/api/records/"

    # Format a request for information on the deposition
    req = Request(
        "{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )

    # If the request fails, return None
    try:
        resp = urlopen(req)
    except Exception as e:
        return None

    # Otherwise, process information about the deposition
    record = json.loads(resp.read().decode("utf-8"))

    now = datetime.now()

    # Get title and description from deposition to create Artifact
    # (All zenodo depositions must have title and description fields)
    item = Artifact(
        title=record['metadata']['title'],
        description=record['metadata']['description'],
        doi=record['conceptrecid'],
        launchable=True,
        created_at=now,
        updated_at=now,
        created_by=user,
        updated_by=user,
    )

    item.authors.set([
        make_author(author['name'])
        for author in record['metadata']['creators']
    ])

    item.save()

    # Create a first version
    item.artifact_versions.create(doi=record['doi'], created_at=now)
    
    return item.pk


def index(request):
    """Load main portal page with search parameters (if relevant)

    Parameters
    ----------
    request : Request
        Get request, possibly with form data
        If form data is present, it should come in the format:
        {
            'search': string,
            'labels': list of numeric strings,
            'is_or': boolean
        }

    Returns
    -------
    HTTPResponse
        Index template, rendered with artifacts matching search specifications
    """

    # Use the index template
    template = loader.get_template('sharing_portal/index.html')

    # Initialize the context to return
    context = {
        'hub_url': JUPYTERHUB_URL,
    }

    # If a 'post' request was made, there are search parameters
    if request.method == 'POST':
        form = LabelForm(request.POST)

        # If the form is valid, parse it
        if form.is_valid():
            try:
                # Pass in form so that the template can show search parameters
                context['form'] = form
                # Pass in the filtered list of artifacts to display
                context['artifacts'] = artifacts_from_form(form.cleaned_data)
            except Exception as e:
                LOG.exception(e)
                # If something goes wrong, fail gracefully
                context['search_failed'] = True
            else:
                # Otherwise, if the list is empty the template will
                # indicate that there were no matching results
                context['search_failed'] = False

            # Render the index in the response
            return HttpResponse(template.render(context, request))

    # If no post request was made, there were no search parameters
    else:
        # Pass in an empty form to show that there are no search parameters
        form = LabelForm()
        context['form'] = form

        # Display all the artifacts when rendering the index page
        context['artifacts'] = Artifact.objects.all()
        return HttpResponse(template.render(context, request))


@login_required
def upload(request):
    """Handle to upload an item from Zenodo to the portal

    Parameters
    ----------
    request: Request
        request, containing a 'doi' query parameter

    Returns
    -------
        Redirect to the portal index
    """
    # If there's no doi, redirect with the error that none was provided
    doi = request.GET.get('doi')
    if doi is None:
        error_message = ("No doi was provided. To upload to the portal, "
                         "include a Zenodo DOI as a query argument")
        messages.add_message(request, messages.INFO, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))

    # Otherwise, briefly load the upload template
    template = loader.get_template('sharing_portal/upload.html')

    # Try to upload the deposition with its doi
    pk = upload_artifact(doi, user=request.user)

    # If no pk was returned, something went wrong
    if pk is None:
        # Return a message to be displayed on the index page
        error_message = "There is no Zenodo publication with that DOI"
        messages.add_message(request, messages.INFO, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))
    # If a pk was returned, the upload was successful
    else:
        # Redirect to the detail page for the newly added artifact
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))


@login_required
def edit_artifact(request, pk):
    artifact = get_object_or_404(Artifact, pk=pk)

    if not (request.user.is_staff or artifact.created_by == request.user):
        messages.add_message(request, messages.ERROR, 'You do not have permission to edit this artifact.')
        return HttpResponseRedirect(reverse('sharing_portal:detail'), args=[pk])

    if request.method == 'POST':
        form = ArtifactForm(request.POST, request.FILES, instance=artifact)
        
        if form.is_valid():
            artifact.updated_by = request.user
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Success')
            return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))
    else:
        form = ArtifactForm(instance=artifact)
    
    template = loader.get_template('sharing_portal/edit.html')
    context = {
        'artifact_form': form, 
        'artifact': artifact,
        'pk': pk,
    }

    return HttpResponse(template.render(context, request))


def edit_redirect(request):
    doi = request.GET.get('doi')
    if not doi:
        error_message = ("A valid DOI is needed to look up an artifact.")
        messages.add_message(request, messages.INFO, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))

    try:
        artifact = Artifact.objects.get(doi=doi)
    except Artifact.DoesNotExist:
        error_message = ("No artifact found for DOI {}".format(doi))
        messages.add_message(request, messages.ERROR, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))

    return HttpResponseRedirect(reverse('sharing_portal:edit', args=[artifact.pk]))


@login_required
def sync_artifact_versions(request, pk):
    artifact = get_object_or_404(Artifact, pk=pk)

    if not (request.user.is_staff or artifact.created_by == request.user):
        messages.add_message(request, messages.ERROR, 'You do not have permission to edit this artifact.')
        return HttpResponseRedirect(reverse('sharing_portal:detail'), args=[pk])

    # Given artifact DOI, fetch all known Zenodo DOIs
    # For each DOI, ensure it exists in our DB (create missing versions)

    messages.add_message(request, messages.SUCCESS, 'The latest versions of this artifact have been synced.')
    return HttpResponseRedirect(reverse('sharing_portal:detail', args=[artifact.pk]))


def sync_artifact_versions_redirect(request):
    doi = request.GET.get('previous_doi', request.GET.get('doi'))

    if not doi:
        error_message = ("A valid DOI is needed to look up an artifact.")
        messages.add_message(request, messages.INFO, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))

    try:
        artifact_version = ArtifactVersion.objects.get(doi=doi)
        artifact = artifact_version.artifact
    except ArtifactVersion.DoesNotExist:
        error_message = ("No artifact version found for DOI {}".format(doi))
        messages.add_message(request, messages.ERROR, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[artifact.pk]))

    # TODO: change to something else
    return HttpResponseRedirect(reverse('sharing_portal:sync_versions', args=[artifact.pk]))


class DetailView(generic.DetailView):
    """Class that returns a basic detailed view of an artifact"""
    model = Artifact
    template_name = 'sharing_portal/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context['editable'] = (
            self.request.user.is_staff or (
            self.object.created_by == self.request.user))
        return context
