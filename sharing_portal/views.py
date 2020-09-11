import json

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import F, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from projects.models import Project
from util.project_allocation_mapper import ProjectAllocationMapper

from .conf import JUPYTERHUB_URL
from .forms import ArtifactForm, ArtifactVersionForm, AuthorFormset, ShareArtifactForm
from .models import Artifact, ArtifactVersion, Author, ShareTarget

import logging
LOG = logging.getLogger(__name__)

SHARING_KEY_PARAM = 's'


def can_edit(request, artifact):
    if artifact.created_by == request.user:
        return True
    if request.user.is_staff:
        return True
    return False


def check_edit_permission(func):
    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop('pk')
        artifact = get_object_or_404(Artifact, pk=pk)
        if not can_edit(request, artifact):
            messages.add_message(request, messages.ERROR,
                'You do not have permission to edit this artifact.')
            return HttpResponseRedirect(reverse('sharing_portal:detail', args=[pk]))
        # Replace pk with Artifact instance to avoid another lookup
        kwargs.setdefault('artifact', artifact)
        return func(request, *args, **kwargs)
    return wrapper


def check_view_permission(func):
    def can_view(request, artifact):
        if artifact.doi:
            return True
        if artifact.sharing_key and (
            request.GET.get(SHARING_KEY_PARAM) == artifact.sharing_key):
            return True

        if request.user.is_authenticated():
            if request.user.is_staff:
                return True
            if artifact.created_by == request.user:
                return True
            project_shares = ShareTarget.objects.filter(
                artifact=artifact, project__isnull=False)
            # Avoid the membership lookup if there are no sharing rules in place
            if project_shares:
                mapper = ProjectAllocationMapper(request)
                user_projects = [
                    p['chargeCode']
                    for p in mapper.get_user_projects(
                        request.user.username, fetch_balance=False)
                ]
                if any(p.charge_code in user_projects for p in project_shares):
                    return True

        return False

    def wrapper(request, *args, **kwargs):
        pk = kwargs.pop('pk')
        artifact = get_object_or_404(Artifact, pk=pk)
        if not can_view(request, artifact):
            raise Http404('The requested artifact does not exist, or you do not have permission to view.')
        # Replace pk with Artifact instance to avoid another lookup
        kwargs.setdefault('artifact', artifact)
        return func(request, *args, **kwargs)
    return wrapper


class ArtifactFilter:
    @staticmethod
    def MINE(request):
        if request.user.is_authenticated():
            return Q(created_by=request.user)
        else:
            return Q()

    PUBLIC = Q(doi__isnull=False)

    @staticmethod
    def PROJECT(projects):
        return Q(shared_to_projects__in=projects)


def _render_list(request, artifacts, user_projects=None):
    if not user_projects:
        if request.user.is_authenticated():
            mapper = ProjectAllocationMapper(request)
            user_projects = mapper.get_user_projects(
                request.user.username, fetch_balance=False)
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
    user_projects = None
    if request.user.is_authenticated():
        mapper = ProjectAllocationMapper(request)
        user_projects = mapper.get_user_projects(
            request.user.username, fetch_balance=False)
        charge_codes = [p['chargeCode'] for p in user_projects]
        projects = Project.objects.filter(charge_code__in=charge_codes)
        f = (ArtifactFilter.MINE(request) | ArtifactFilter.PROJECT(projects) | ArtifactFilter.PUBLIC)
    else:
        f = ArtifactFilter.PUBLIC

    artifacts = Artifact.objects.filter(f)
    # Pass user_projects to list to avoid a second fetch of this data
    return _render_list(request, artifacts, user_projects=user_projects)


@login_required
def index_mine(request):
    artifacts = Artifact.objects.filter(ArtifactFilter.MINE(request))
    return _render_list(request, artifacts)


def index_public(request):
    artifacts = Artifact.objects.filter(ArtifactFilter.PUBLIC)
    return _render_list(request, artifacts)


def index_project(request, charge_code):
    projects = Project.objects.filter(charge_code=charge_code)
    artifacts = Artifact.objects.filter(ArtifactFilter.PROJECT(projects))
    return _render_list(request, artifacts)


@check_edit_permission
@login_required
def edit_artifact(request, artifact):
    if request.method == 'POST':
        form = ArtifactForm(request.POST, instance=artifact)

        if 'delete_version' in request.POST:
            version_id = request.POST.get('delete_version')
            try:
                version = artifact.versions.get(pk=version_id)
                version.delete()
                messages.add_message(request, messages.SUCCESS,
                    'Successfully deleted artifact version.')
            except ArtifactVersion.DoesNotExist:
                messages.add_message(request, messages.ERROR,
                    'Artifact version {} does not exist'.format(version_id))
            # Return to edit form
            return HttpResponseRedirect(
                reverse('sharing_portal:edit', args=[artifact.pk]))

        artifact, errors = _handle_artifact_forms(request, form)
        if errors:
            (messages.add_message(request, messages.ERROR, e) for e in errors)
        else:
            messages.add_message(request, messages.SUCCESS, 'Successfully saved artifact.')
        return HttpResponseRedirect(
            reverse('sharing_portal:detail', args=[artifact.pk]))

    form = ArtifactForm(instance=artifact)
    template = loader.get_template('sharing_portal/edit.html')
    context = {
        'artifact_form': form,
        'artifact': artifact,
        'all_versions': _artifact_display_versions(artifact),
    }

    return HttpResponse(template.render(context, request))


@check_edit_permission
@login_required
def share_artifact(request, artifact):
    if request.method == 'POST':
        form = ShareArtifactForm(request.POST)

        if form.is_valid():
            existing_targets = ShareTarget.objects.filter(artifact=artifact)
            existing_project_shares = [st.project for st in existing_targets if st.project]
            incoming_project_shares = form.cleaned_data['projects']
            for p in existing_project_shares:
                if p not in incoming_project_shares:
                    (ShareTarget.objects.filter(artifact=artifact, project=p)
                        .delete())
                    LOG.info('Un-shared artifact %s to project %s', artifact.pk, p.pk)
            for p in incoming_project_shares:
                if p not in existing_project_shares:
                    ShareTarget.objects.create(artifact=artifact, project=p)
                    LOG.info('Shared artifact %s to project %s', artifact.pk, p.pk)
            messages.add_message(request, messages.SUCCESS,
                'Successfully updated sharing settings')
            return HttpResponseRedirect(reverse('sharing_portal:detail', args=[artifact.pk]))
    else:
        form = ShareArtifactForm(initial={
            'projects': artifact.shared_to_projects.all(),
        })

    share_url = request.build_absolute_uri(
        reverse('sharing_portal:detail', kwargs={'pk': artifact.pk}))
    if artifact.sharing_key:
        share_url += '?{key_name}={key_value}'.format(
            key_name=SHARING_KEY_PARAM,
            key_value=artifact.sharing_key)

    template = loader.get_template('sharing_portal/share.html')
    context = {
        'share_form': form,
        'share_url': share_url,
        'artifact': artifact,
    }

    return HttpResponse(template.render(context, request))


@check_view_permission
def artifact(request, artifact, version_idx=None):
    version = _artifact_version(artifact, version_idx)

    if not version:
        error_message = 'This artifact has no version {}'.format(version_idx)
        messages.add_message(request, messages.ERROR, error_message)

    if version_idx:
        launch_url = reverse('sharing_portal:launch_version',
            args=[artifact.pk, version_idx])
    else:
        launch_url = reverse('sharing_portal:launch', args=[artifact.pk])

    # Ensure launch URLs are authenticated if a private link is being used.
    if SHARING_KEY_PARAM in request.GET:
        launch_url += '?{}={}'.format(SHARING_KEY_PARAM, request.GET[SHARING_KEY_PARAM])

    template = loader.get_template('sharing_portal/detail.html')
    context = {
        'artifact': artifact,
        'all_versions': _artifact_display_versions(artifact),
        'version': version,
        'launch_url': launch_url,
        'related_artifacts': artifact.related_items,
        'editable': (
            request.user.is_staff or (
            artifact.created_by == request.user)),
    }

    return HttpResponse(template.render(context, request))


@check_view_permission
def launch(request, artifact, version_idx=None):
    version = _artifact_version(artifact, version_idx)

    if not version:
        raise Http404((
            'There is no version {} for this artifact.'
            .format(version_idx or '')))

    version.launch_count = F('launch_count') + 1
    version.save(update_fields=['launch_count'])
    return redirect(version.launch_url(can_edit=can_edit(request, artifact)))


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
@login_required
def embed_create(request):
    return _embed_form(request, form_title='Create artifact')


@check_edit_permission
@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
@login_required
def embed_edit(request, artifact):
    context = {}
    if 'new_version' in request.GET:
        context['form_title'] = 'Create new version of artifact'
    else:
        context['form_title'] = 'Edit artifact'

    return _embed_form(request, artifact=artifact, context=context)


@csp_update(FRAME_ANCESTORS=JUPYTERHUB_URL)
def embed_cancel(request):
    return _embed_callback(request, dict(status='cancel'))


def _embed_form(request, artifact=None, context={}):
    new_version = (not artifact) or ('new_version' in request.GET)

    if request.method == 'POST':
        form = ArtifactForm(request.POST, instance=artifact)
        authors_formset = AuthorFormset(request.POST)
        if (not artifact) or new_version:
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
                    'deposition_id': request.GET.get('deposition_id'),
                    'deposition_repo': request.GET.get('deposition_repo')
                })
        else:
            version_form = None

    template = loader.get_template('sharing_portal/embed.html')
    context.update({
        'artifact_form': form,
        'authors_formset': authors_formset,
        'version_form': version_form,
    })

    return HttpResponse(template.render(context, request))

def _embed_callback(request, payload):
    template = loader.get_template('sharing_portal/embed_callback.html')
    payload_wrapper = dict(
        message='save_result',
        body=payload,
    )
    context = {
        'payload_json': json.dumps(payload_wrapper),
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


def _artifact_display_versions(artifact):
    """Return a list of artifact versions for display purposes.

    This is slightly different than the 'versions' property of the artifact, as
    it is reverse-sorted (newest at the top) and also enumerated so that while
    it's reversed, the numbers still indicate chronological order.
    """
    versions = list(artifact.versions)
    return [(len(versions) - i, v) for (i, v) in enumerate(reversed(versions))]
