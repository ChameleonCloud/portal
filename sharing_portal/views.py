from datetime import datetime
import logging
import json
from urllib.request import urlopen, Request

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.utils.dateparse import parse_datetime
from django.views import generic
from util.project_allocation_mapper import ProjectAllocationMapper

from .conf import JUPYTERHUB_URL, ZENODO_SANDBOX
from .forms import ArtifactForm, ArtifactVersionForm, AuthorFormset, LabelForm
from .models import Artifact, ArtifactVersion, Author, Label
from .zenodo import ZenodoClient

LOG = logging.getLogger(__name__)

class ArtifactFilter:
    @staticmethod
    def MINE(request):
        if request.user.is_authenticated():
            return Q(created_by=request.user)
        else:
            return Q()

    PUBLIC = Q(doi__isnull=False)


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
        doi=record['conceptdoi'],
        launchable=True,
        created_at=now,
        updated_at=now,
        created_by=user,
        updated_by=user,
    )

    item.save()

    item.authors.set([
        make_author(author['name'])
        for author in record['metadata']['creators']
    ])

    # Create a first version
    item.artifact_versions.create(doi=record['doi'], created_at=now)

    return item.pk


def _render_list(request, artifacts):
    if request.user.is_authenticated():
        mapper = ProjectAllocationMapper(request)
        user_projects = mapper.get_user_projects(request.user.username)
    else:
        user_projects = []

    template = loader.get_template('sharing_portal/index.html')
    context = {
        'hub_url': JUPYTERHUB_URL,
        'artifacts': artifacts.order_by('-created_at'),
        'projects': user_projects,
    }

    return HttpResponse(template.render(context, request))


def index_all(request, collection=None):
    artifacts = Artifact.objects.filter(
        ArtifactFilter.MINE(request) | ArtifactFilter.PUBLIC)

    return _render_list(request, artifacts)


@login_required
def index_mine(request):
    artifacts = Artifact.objects.filter(ArtifactFilter.MINE(request))
    return _render_list(request, artifacts)


def index_public(request):
    artifacts = Artifact.objects.filter(ArtifactFilter.PUBLIC)
    return _render_list(request, artifacts)


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

    # Make sure no artifact version exists already for this DOI
    if ArtifactVersion.objects.filter(doi=doi).count() > 0:
        error_message = "An artifact already exists for that DOI"
        messages.add_message(request, messages.ERROR, error_message)
        return HttpResponseRedirect(reverse('sharing_portal:index'))

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
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))

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
    zenodo = ZenodoClient()
    artifact = get_object_or_404(Artifact, pk=pk)
    # We will always go back to the detail view
    response = HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))

    if not (request.user.is_staff or artifact.created_by == request.user):
        messages.add_message(request, messages.ERROR, 'You do not have permission to edit this artifact.')
        return response

    try:
        versions = zenodo.get_versions(artifact.doi)

        for version in versions:
            version_doi = version['doi']
            version_created = parse_datetime(version['created'])
            existing = artifact.artifact_versions.get(doi=version_doi)
            if not existing:
                artifact.artifact_versions.create(doi=version_doi, created_at=version_created)
                if artifact.updated_at < version_created:
                    artifact.updated_at = version_created
                    artifact.save()

    except Exception as e:
        LOG.exception(e)
        messages.add_message(request, messages.ERROR, 'Could not sync versions for this artifact.')
        return response

    messages.add_message(request, messages.SUCCESS, 'The latest versions of this artifact have been synced.')
    return response


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

    return HttpResponseRedirect(reverse('sharing_portal:sync_versions', args=[artifact.pk]))


def artifact(request, pk, version_idx=None):
    artifact = get_object_or_404(Artifact, pk=pk)

    template = loader.get_template('sharing_portal/detail.html')

    artifact_versions = list(artifact.versions)
    if artifact_versions:
        version = artifact_versions[-1]
    else:
        LOG.error('Artifact {} has no versions'.format(pk))
        version = None

    if version_idx:
        try:
            # Version path parameters are 1-indexed
            version = artifact_versions[int(version_idx) - 1]
        except IndexError, ValueError:
            error_message = 'This artifact has no version {}'.format(version_idx)
            messages.add_message(request, messages.ERROR, error_message)
            pass

    context = {
        'artifact': artifact,
        'all_versions': [(len(artifact_versions) - i, v) for (i, v) in enumerate(reversed(artifact_versions))],
        'version': version,
        'related_artifacts': artifact.related_items,
        'editable': (
            request.user.is_staff or (
            artifact.created_by == request.user)),
    }

    return HttpResponse(template.render(context, request))


@csp_update(FRAME_ANCESTORS='localhost:8888')
def create_artifact_embed(request):
    artifact_id = request.GET.get('artifact_id')


@csp_update(FRAME_ANCESTORS='localhost:8888')
def edit_artifact_embed(request, pk):
    artifact = get_object_or_404(Artifact, pk=pk)

    if not (request.user.is_staff or artifact.created_by == request.user):
        # Return error page
        messages.add_message(request, messages.ERROR,
            'You do not have permission to edit this artifact.')
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))

    new_version = 'new_version' in request.GET

    if request.method == 'POST':
        form = ArtifactForm(request.POST, instance=artifact)
        authors_formset = AuthorFormset(request.POST)
        if new_version:
            version_form = ArtifactVersionForm(request.POST)
        else:
            version_form = None

        if form.is_valid():
            artifact = form.save(commit=False)
            authors = None
            version = None

            if authors_formset.is_valid():
                # Save the list of authors. First we save the new authors items
                # (users may have added new authors). Then we get the list of
                # all author models in the formset and replace the 'authors'
                # m2m list of the artifact. There are probably less ugly ways
                # of doing this, but this is a weird form.
                authors_formset.save()
                authors = [
                    f.instance for f in authors_formset.forms
                    if f.instance.pk is not None and
                    (f.instance not in authors_formset.deleted_objects)
                ]
            else:
                messages.add_message(request, messages.ERROR, authors_formset.errors)

            if version_form:
                if version_form.is_valid():
                    version = version_form.save(commit=False)
                    # Remove the version form to prevent re-submit
                    version_form = None
                else:
                    messages.add_message(request, messages.ERROR, version_form.errors)

            artifact.updated_by = request.user
            if authors:
                artifact.authors.set(authors)
            if version:
                artifact.versions.add(version)
            artifact.save()
        else:
            messages.add_message(request, messages.ERROR, form.errors)
    else:
        form = ArtifactForm(instance=artifact)
        authors_formset = AuthorFormset(queryset=artifact.authors.all())
        if new_version:
            version_form = ArtifactVersionForm(
                initial={
                    'deposition_id': request.GET.get('artifact_id'),
                    'deposition_repo': request.GET.get('artifact_repo')
                })
        else:
            version_form = None

    template = loader.get_template('sharing_portal/edit_embed.html')

    context = {
        'artifact_form': form,
        'authors_formset': authors_formset,
        'version_form': version_form,
        'artifact': artifact,
        'pk': pk,
    }

    return HttpResponse(template.render(context, request))
