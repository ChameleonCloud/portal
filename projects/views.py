from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from chameleon.decorators import terms_required
from django.contrib import messages
from django.http import (Http404, HttpResponse,
                         HttpResponseRedirect, HttpResponseNotAllowed)
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django import forms
from datetime import datetime

from pytas.http import TASClient
from pytas.models import Project

from forms import ProjectCreateForm, ProjectAddUserForm, AllocationCreateForm

import re
import logging
import json

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

    tas = TASClient()
    user = tas.get_user(username=request.user)
    context['is_pi_eligible'] = user['piEligibility'] == 'Eligible'

    projects = Project.list(username=request.user)
    projects = list(p for p in projects if p.source == 'Chameleon')

    context['projects'] = projects

    return render(request, 'projects/user_projects.html', context)


@login_required
def view_project(request, project_id):
    try:
        project = Project(project_id)
        if project.source != 'Chameleon':
            raise Http404('The requested project does not exist!')
    except Exception as e:
        logger.error(e)
        raise Http404('The requested project does not exist!')

    if request.POST:
        if 'add_user' in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                # try to add user
                try:
                    add_username = form.cleaned_data['username']
                    if project.add_user(add_username):
                        messages.success(request,
                            'User "%s" added to project!' % add_username)
                        form = ProjectAddUserForm()
                except:
                    logger.exception('Failed adding user')
                    form.add_error('username', '')
                    form.add_error('__all__', 'Unable to add user. Confirm that the '
                        'username is correct.')
            else:
                form.add_error('__all__', 'There were errors processing your request. '
                    'Please see below for details.')
        else:
            form = ProjectAddUserForm()

        if 'del_user' in request.POST:
            # try to remove user
            try:
                del_username = request.POST['username']
                if project.remove_user(del_username):
                    messages.success(request, 'User "%s" removed from project' % del_username)
            except:
                logger.exception('Failed removing user')
                messages.error(request, 'An unexpected error occurred while attempting '
                    'to remove this user. Please try again')

    else:
        form = ProjectAddUserForm()

    users = project.get_users()

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    project.active_allocations = []
    project.pending_allocations = []
    project.rejected_allocations = []
    project.inactive_allocations = []

    for a in project.allocations:
        if a.status == 'Active' and a.resource == 'Chameleon':
            project.active_allocations.append(a)
            project.has_active_allocations = True
        if a.status == 'Pending' and a.resource == 'Chameleon':
            project.pending_allocations.append(a)
            project.has_pending_allocations = True
        if a.status == 'Inactive' and a.resource == 'Chameleon':
            project.inactive_allocations.append(a)
            project.has_inactive_allocations = True
        if a.status == 'Rejected' and a.resource == 'Chameleon':
            project.rejected_allocations.append(a)
            project.has_rejected_allocations = True


        if a.start and isinstance(a.start, basestring):
            a.start = datetime.strptime(a.start, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateRequested:
            if isinstance(a.dateRequested, basestring):
                a.dateRequested = datetime.strptime(a.dateRequested, '%Y-%m-%dT%H:%M:%SZ')
        if a.dateReviewed:
            if isinstance(a.dateReviewed, basestring):
                a.dateReviewed = datetime.strptime(a.dateReviewed, '%Y-%m-%dT%H:%M:%SZ')
        if a.end:
            if isinstance(a.end, basestring):
                a.end = datetime.strptime(a.end, '%Y-%m-%dT%H:%M:%SZ')

            days_left = (a.end - datetime.today()).days
            if days_left >= 0 and days_left <= 90:
                a.up_for_renewal = True
                a.renewal_days = days_left

    return render(request, 'projects/view_project.html', {
        'project': project,
        'users': users,
        'is_pi': request.user.username == project.pi.username,
        'form': form,
    })


@login_required
@terms_required('project-terms')
def create_allocation(request, project_id, allocation_id=-1):
    tas = TASClient()

    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request,
                       'Only PI Eligible users can request allocations. If you would '
                       'like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))

    project = Project(project_id)
    allocation = None
    if allocation_id > 0:
        for a in project.allocations:
            if a.id == int(allocation_id):
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

            supplemental_details = allocation.pop('supplemental_details', '(none)')
            funding_source = allocation.pop('funding_source', None)

            if not supplemental_details:
                supplemental_details = '(none)'

            if funding_source:
                allocation['justification'] = '%s\n\n--- Funding source(s) ---\n\n%s' % (
                    supplemental_details, funding_source)
            else:
                allocation['justification'] = supplemental_details

            allocation['projectId'] = project_id
            allocation['requestorId'] = tas.get_user(username=request.user)['id']
            allocation['resourceId'] = '39'

            if allocation_id > 0:
                allocation['id'] = allocation_id

            try:
                logger.info('Submitting allocation request for project %s: %s' %
                            (project.id, allocation))
                updated_project = tas.edit_project(project.as_dict())
                tas.create_allocation(allocation)
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
    tas = TASClient()
    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request,
                       'Only PI Eligible users can create new projects. '
                       'If you would like to request PI Eligibility, please '
                       '<a href="/user/profile/edit/">submit a PI Eligibility '
                       'request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))
    if request.POST:
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()
            project.pop('accept_project_terms', None)

            # pi
            pi_user = tas.get_user(username=request.user)
            project['piId'] = pi_user['id']

            # allocations
            allocation = {
                'resourceId': 39,
                'requestorId': pi_user['id'],
                'computeRequested': 20000,
            }
            supplemental_details = allocation.pop('supplemental_details', '(none)')
            funding_source = allocation.pop('funding_source', None)

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
                created_project = tas.create_project(project)
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
        form = ProjectCreateForm()

    return render(request, 'projects/create_project.html', {'form': form})


@login_required
def edit_project(request):
    context = {}
    return render(request, 'projects/edit_project.html', context)

