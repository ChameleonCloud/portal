from datetime import datetime
import logging
import json
from urllib.request import urlopen, Request

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import F, Q
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
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
def edit_artifact(request, pk):
    artifact = get_object_or_404(Artifact, pk=pk)

    if not (request.user.is_staff or artifact.created_by == request.user):
        messages.add_message(request, messages.ERROR, 'You do not have permission to edit this artifact.')
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))

    if request.method == 'POST':
        form = ArtifactForm(request.POST, request.FILES, instance=artifact)

        artifact, errors = _handle_artifact_forms(request, form)
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


def artifact(request, pk, version_idx=None):
    artifact = get_object_or_404(Artifact, pk=pk)
    version = _artifact_version(artifact, version_idx)
    artifact_versions = list(artifact.versions)

    if not version:
        error_message = 'This artifact has no version {}'.format(version_idx)
        messages.add_message(request, messages.ERROR, error_message)

    if version_idx:
        launch_url = reverse('sharing_portal:launch_version',
            args=[artifact.pk, version_idx])
    else:
        launch_url = reverse('sharing_portal:launch', args=[artifact.pk])

    template = loader.get_template('sharing_portal/detail.html')
    context = {
        'artifact': artifact,
        'all_versions': [(len(artifact_versions) - i, v) for (i, v) in enumerate(reversed(artifact_versions))],
        'version': version,
        'launch_url': launch_url,
        'related_artifacts': artifact.related_items,
        'editable': (
            request.user.is_staff or (
            artifact.created_by == request.user)),
    }

    return HttpResponse(template.render(context, request))


def launch(request, pk, version_idx=None):
    artifact = get_object_or_404(Artifact, pk=pk)
    version = _artifact_version(artifact, version_idx)

    if version:
        version.launch_count = F('launch_count') + 1
        version.save(update_fields=['launch_count'])
        return redirect(version.launch_url)
    else:
        return Http404()


def _artifact_version(artifact, version_idx=None):
    artifact_versions = list(artifact.versions)
    # A default of 0 means get the most recent artifact version.
    # Version indices are 1-indexed.
    version_idx = version_idx or 0
    try:
        return artifact_versions[int(version_idx) - 1]
    except IndexError, ValueError:
        return None


@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
def embed_create(request):
    return _embed_form(request, form_title='Create artifact')


@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
def embed_edit(request, pk):
    artifact = get_object_or_404(Artifact, pk=pk)

    if not (request.user.is_staff or artifact.created_by == request.user):
        # Return error page
        messages.add_message(request, messages.ERROR,
            'You do not have permission to edit this artifact.')
        return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))

    return _embed_form(request, form_title='Edit artifact', artifact=artifact)


@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
def embed_cancel(request):
    return _embed_callback(request, dict(status='cancel'))


def _embed_form(request, form_title=None, artifact=None):
    new_version = (not artifact) or ('new_version' in request.GET)

    if request.method == 'POST':
        form = ArtifactForm(request.POST, instance=artifact)
        authors_formset = AuthorFormset(request.POST)
        if (not artifact) or add_version:
            version_form = ArtifactVersionForm(request.POST)
        else:
            version_form = None

        artifact, errors = _handle_artifact_forms(request, form,
            authors_formset=authors_formset, version_form=version_form)

        if not errors:
            return _embed_callback(request, dict(status='success', id=artifact.pk))
        else:
            # Fail through and return to form with errors displayed
            for err in errors:
                messages.add_message(request, messages.ERROR, err)
    else:
        form = ArtifactForm(instance=artifact)
        if artifact:
            queryset = artifact.authors.all()
            initial = None
        else:
            queryset = Author.objects.none()
            # Default to logged-in user
            initial = [{'name': request.user.get_full_name()}]
        authors_formset = AuthorFormset(queryset=queryset, initial=initial)
        if new_version:
            version_form = ArtifactVersionForm(
                initial={
                    'deposition_id': request.GET.get('artifact_id'),
                    'deposition_repo': request.GET.get('artifact_repo')
                })
        else:
            version_form = None

    template = loader.get_template('sharing_portal/embed.html')
    context = {
        'form_title': form_title,
        'artifact_form': form,
        'authors_formset': authors_formset,
        'version_form': version_form,
    }

    return HttpResponse(template.render(context, request))

def _embed_callback(request, payload):
    template = loader.get_template('sharing_portal/embed_callback.html')
    context = {
        'payload_json': json.dumps(payload),
        'jupyterhub_origin': JUPYTERHUB_URL,
    }

    return HttpResponse(template.render(context, request))


def _handle_artifact_forms(request, artifact_form, authors_formset=None,
                           version_form=None):
    artifact = None
    errors = []

    if artifact_form.is_valid():
        artifact = artifact_form.save(commit=False)
        authors = None
        version = None

        if authors_formset:
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
                errors.extend(authors_formset.errors)

        if version_form:
            if version_form.is_valid():
                version = version_form.save(commit=False)
                # Remove the version form to prevent re-submit
                version_form = None
            else:
                errors.extend(version_form.errors)

        if not errors:
            if not artifact.pk:
                artifact.created_by = request.user
            artifact.updated_by = request.user
            artifact.save()
            if authors:
                artifact.authors.set(authors)
            if version:
                version.artifact = artifact
                version.save()
    else:
        errors.extend(artifact_form.errors)

    return artifact, errors
