from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from chameleon.decorators import terms_required
from django.contrib import messages
from django.http import (Http404, HttpResponseForbidden, HttpResponse,
                         HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse)
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django import forms
from datetime import datetime
from django.conf import settings
from .models import Project, ProjectExtras
from projects.serializer import ProjectExtrasJSONSerializer
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from .forms import ProjectCreateForm, ProjectAddUserForm,\
    AllocationCreateForm, EditNicknameForm, AddBibtexPublicationForm
from django.db import IntegrityError
import re
import logging
import json
from keystoneclient.v3 import client as ks_client
from keystoneauth1 import adapter
from django.conf import settings
import uuid
import sys
from chameleon.keystone_auth import admin_ks_client, sync_projects, get_user
from util.project_allocation_mapper import ProjectAllocationMapper

logger = logging.getLogger('projects')


def project_pi_or_admin_or_superuser(user, project):
    if user.is_superuser:
        return True

    if user.groups.filter(name='Allocation Admin').count() == 1:
        return True

    if user.username == project.pi.username:
        return True

    return False

def project_member_or_admin_or_superuser(user, project, project_user):
    if project_pi_or_admin_or_superuser(user, project):
        return True

    for pu in project_user:
        if user.username == pu.username:
            return True

    return False

@login_required
def user_projects(request):
    context = {}

    username = request.user.username
    mapper = ProjectAllocationMapper(request)
    user = mapper.get_user(username)

    context['is_pi_eligible'] = user['piEligibility'].lower() == 'eligible'
    context['username'] = username
    context['projects'] = mapper.get_user_projects(username, to_pytas_model=True)

    return render(request, 'projects/user_projects.html', context)

@login_required
def view_project(request, project_id):
    mapper = ProjectAllocationMapper(request)
    try:
        project = mapper.get_project(project_id)
        if project.source != 'Chameleon':
            raise Http404('The requested project does not exist!')
    except Exception as e:
        logger.error(e)
        raise Http404('The requested project does not exist!')

    form = ProjectAddUserForm()
    nickname_form = EditNicknameForm()
    pubs_form = AddBibtexPublicationForm()

    if request.POST and project_pi_or_admin_or_superuser(request.user, project):
        form = ProjectAddUserForm()
        if 'add_user' in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                try:
                    add_username = form.cleaned_data['username']
                    if mapper.add_user_to_project(project, add_username):
                        sync_project_memberships(request, add_username)
                        messages.success(request,
                            f'User "{add_username}" added to project!')
                        form = ProjectAddUserForm()
                except Exception as e:
                    logger.exception('Failed adding user')
                    messages.error(request, (
                        'Unable to add user. Confirm that the username is '
                        'correct and corresponds to a current Chameleon user.'))
            else:
                messages.error(request, (
                    'There were errors processing your request. '
                    'Please see below for details.'))
        elif 'del_user' in request.POST:
            try:
                del_username = request.POST['username']
                # Ensure that it's not possible to remove the PI
                if del_username == project.pi.username:
                    raise PermissionDenied('Removing the PI from the project is not allowed.')
                if mapper.remove_user_from_project(project, del_username):
                    sync_project_memberships(request, del_username)
                    messages.success(request, 'User "%s" removed from project' % del_username)
            except PermissionDenied as exc:
                messages.error(request, exc)
            except:
                logger.exception('Failed removing user')
                messages.error(request, 'An unexpected error occurred while attempting '
                    'to remove this user. Please try again')
        elif 'nickname' in request.POST:
            nickname_form = edit_nickname(request, project_id)

    users = mapper.get_project_members(project)

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    for a in project.allocations:
        if a.start and isinstance(a.start, str):
            a.start = datetime.strptime(a.start, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateRequested:
            if isinstance(a.dateRequested, str):
                a.dateRequested = datetime.strptime(a.dateRequested, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateReviewed:
            if isinstance(a.dateReviewed, str):
                a.dateReviewed = datetime.strptime(a.dateReviewed, '%Y-%m-%dT%H:%M:%SZ')
        if a.end:
            if isinstance(a.end, str):
                a.end = datetime.strptime(a.end, '%Y-%m-%dT%H:%M:%SZ')

    user_mashup = []
    for u in users:
        user = {
            'username': u.username,
            'role': u.role,
        }
        try:
            portal_user = User.objects.get(username=u.username)
            user['email'] = portal_user.email
            user['first_name'] = portal_user.first_name
            user['last_name'] = portal_user.last_name
        except User.DoesNotExist:
            logger.info('user: ' + u.username + ' not found')
        user_mashup.append(user)

    return render(request, 'projects/view_project.html', {
        'project': project,
        'project_nickname': project.nickname,
        'users': user_mashup,
        'is_pi': request.user.username == project.pi.username,
        'form': form,
        'nickname_form': nickname_form,
        'pubs_form': pubs_form
    })

def set_ks_project_nickname(chargeCode, nickname):
    for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
        ks_admin = admin_ks_client(region=region)
        project_list = ks_admin.projects.list(domain=ks_admin.user_domain_id)
        project = [this for this in project_list if getattr(this, 'charge_code', None) == chargeCode]
        logger.info('Assigning nickname {0} to project with charge code {1} at {2}'.format(nickname, chargeCode, region))
        if project and project[0]:
            project = project[0]
        ks_admin.projects.update(project, name=nickname)
        logger.info('Successfully assigned nickname {0} to project with charge code {1} at {2}'.format(nickname, chargeCode, region))


def sync_project_memberships(request, username):
    """Re-sync a user's Keystone project memberships.

    This calls utils.auth.keystone_auth.sync_projects under the hood, which
    will dynamically create missing projects as well.

    Args:
        request (Request): the parent request; used for region detection.
        username (str): the username to sync memberships for.

    Return:
        List[keystone.Project]: a list of Keystone projects the user is a
            member of.
    """
    mapper = ProjectAllocationMapper(request)
    try:
        ks_admin = admin_ks_client(request=request)
        ks_user = get_user(ks_admin, username)

        if not ks_user:
            logger.error((
                'Could not fetch Keystone user for {}, skipping membership syncing'
                .format(username)))
            return

        active_projects = mapper.get_user_projects(username,
            alloc_status=['Active'], to_pytas_model=True)

        return sync_projects(ks_admin, ks_user, active_projects)
    except Exception as e:
        logger.error('Could not sync project memberships for %s: %s',
            username, e)
        return []

@login_required
@terms_required('project-terms')
def create_allocation(request, project_id, allocation_id=-1):
    mapper = ProjectAllocationMapper(request)

    user = mapper.get_user(request.user.username)
    if user['piEligibility'].lower() != 'eligible':
        messages.error(request,
                       'Only PI Eligible users can request allocations. If you would '
                       'like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))

    project = mapper.get_project(project_id)

    allocation = None
    allocation_id = int(allocation_id)
    if allocation_id > 0:
        for a in project.allocations:
            if a.id == allocation_id:
                allocation = a

    # goofiness that we should clean up later; requires data cleansing
    abstract = project.description
    if '--- Supplemental details ---' in abstract:
        additional = abstract.split('\n\n--- Supplemental details ---\n\n')
        abstract = additional[0]
        additional = additional[1].split('\n\n--- Funding source(s) ---\n\n')
        justification = additional[0]
        if len(additional) > 1:
            funding_source = additional[1]
        else:
            funding_source = ''
    elif allocation:
        justification = allocation.justification
        if '--- Funding source(s) ---' in justification:
            parts = justification.split('\n\n--- Funding source(s) ---\n\n')
            justification = parts[0]
            funding_source = parts[1]
        else:
            funding_source = ''
    else:
        justification = ''
        funding_source = ''

    if request.POST:
        form = AllocationCreateForm(request.POST,
                                    initial={'description': abstract,
                                             'supplemental_details': justification,
                                             'funding_source': funding_source})
        if form.is_valid():
            allocation = form.cleaned_data.copy()
            allocation['computeRequested'] = 20000

            # Also update the project
            project.description = allocation.pop('description', None)

            supplemental_details = allocation.pop('supplemental_details', None)

            logger.error(supplemental_details)
            funding_source = allocation.pop('funding_source', None)

            #if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            # This is required
            if not supplemental_details:
                supplemental_details = '(none)'

            logger.error(supplemental_details)

            if funding_source:
                allocation['justification'] = '%s\n\n--- Funding source(s) ---\n\n%s' % (
                    supplemental_details, funding_source)
            else:
                allocation['justification'] = supplemental_details

            allocation['projectId'] = project_id
            allocation['requestorId'] = mapper.get_portal_user_id(request.user.username)
            allocation['resourceId'] = '39'

            if allocation_id > 0:
                allocation['id'] = allocation_id

            try:
                logger.info('Submitting allocation request for project %s: %s' %
                            (project.id, allocation))
                updated_project = mapper.save_project(project.as_dict())
                mapper.save_allocation(allocation, project.chargeCode, request.get_host())
                messages.success(request, 'Your allocation request has been submitted!')
                return HttpResponseRedirect(
                    reverse('projects:view_project', args=[updated_project['id']]))
            except:
                logger.exception('Error creating allocation')
                form.add_error('__all__',
                               'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__',
                           'There were errors processing your request. '
                           'Please see below for details.')
    else:
        form = AllocationCreateForm(initial={'description': abstract,
                                             'supplemental_details': justification,
                                             'funding_source': funding_source})
    context = {
        'form': form,
        'project': project,
        'alloc_id': allocation_id,
        'alloc': allocation
    }
    return render(request, 'projects/create_allocation.html', context)


@login_required
@terms_required('project-terms')
def create_project(request):
    mapper = ProjectAllocationMapper(request)
    form_args = {'request': request}

    user = mapper.get_user(request.user.username)
    if user['piEligibility'].lower() != 'eligible':
        messages.error(request,
                       'Only PI Eligible users can create new projects. '
                       'If you would like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))
    if request.POST:
        form = ProjectCreateForm(request.POST, **form_args)
        if form.is_valid():
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()
            # let's check that any provided nickname is unique
            project['nickname'] = project['nickname'].strip()
            nickname_valid = project['nickname'] and \
                             ProjectExtras.objects.filter(nickname=project['nickname']).count() < 1 and \
                             Project.objects.filter(nickname=project['nickname']).count() < 1

            if not nickname_valid:
                form.add_error('__all__',
                            'Project nickname unavailable')
                return render(request, 'projects/create_project.html', {'form': form})

            project.pop('accept_project_terms', None)

            # pi
            pi_user_id = mapper.get_portal_user_id(request.user.username)
            project['piId'] = pi_user_id

            # allocations
            allocation = {
                'resourceId': 39,
                'requestorId': pi_user_id,
                'computeRequested': 20000,
            }

            supplemental_details = project.pop('supplemental_details', None)
            funding_source = project.pop('funding_source', None)

            #if supplemental_details == None:
            #    raise forms.ValidationError("Justifcation is required")
            if not supplemental_details:
                supplemental_details = '(none)'

            if funding_source:
                allocation['justification'] = '%s\n\n--- Funding source(s) ---\n\n%s' % (
                    supplemental_details, funding_source)
            else:
                allocation['justification'] = supplemental_details

            project['allocations'] = [allocation]

            # startup
            project['typeId'] = 2

            # source
            project['source'] = 'Chameleon'
            try:
                created_project = mapper.save_project(project, request.get_host())
                logger.info('newly created project: ' + json.dumps(created_project))
                messages.success(request, 'Your project has been created!')
                return HttpResponseRedirect(
                    reverse('projects:view_project', args=[created_project['id']]))
            except:
                logger.exception('Error creating project')
                form.add_error('__all__',
                               'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__',
                           'There were errors processing your request. '
                           'Please see below for details.')
    else:
        form = ProjectCreateForm(**form_args)

    return render(request, 'projects/create_project.html', {'form': form})


@login_required
def edit_project(request):
    context = {}
    return render(request, 'projects/edit_project.html', context)

@require_POST
def edit_nickname(request, project_id):
    mapper = ProjectAllocationMapper(request)
    project = mapper.get_project(project_id)
    if not project_pi_or_admin_or_superuser(request.user, project):
        messages.error(request, 'Only the project PI can update nickname.')
        return EditNicknameForm()

    form = EditNicknameForm(request.POST)
    if form.is_valid(request):
        # try to update nickname
        try:
            nickname = form.cleaned_data['nickname']
            ProjectAllocationMapper.update_project_nickname(project_id,
                project.chargeCode, nickname)
            form = EditNicknameForm()
            set_ks_project_nickname(project.chargeCode, nickname)
            messages.success(request, 'Update Successful')
        except:
            messages.error(request, 'Nickname not available')
    else:
        messages.error(request, 'Nickname not available')

    return form

def get_extras(request):
    provided_token = request.GET.get('token') if request.GET.get('token') else None
    stored_token = getattr(settings, 'PROJECT_EXTRAS_API_TOKEN', None)
    if not provided_token or not stored_token or provided_token != stored_token:
        logger.error('Project Extras json api Access Token validation failed')
        return HttpResponseForbidden()

    logger.info('Get all project extras json endpoint requested')
    response = {
        'status': 'success'
    }
    try:
        serializer = ProjectExtrasJSONSerializer()
        response['message'] = ''
        extras = json.loads(serializer.serialize(ProjectExtras.objects.all()))
        response['result'] = extras
    except ProjectExtras.DoesNotExist:
        response['message'] = 'Does not exist.'
        response['result'] = None
    return JsonResponse(response)
