from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from chameleon.decorators import terms_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django import forms
from datetime import datetime, timedelta

from pytas.http import TASClient
from pytas.models import Project

from forms import ProjectCreateForm, ProjectAddUserForm, AllocationCreateForm
import project_util

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
    project = Project.get(project_id)

    if request.POST:
        if 'add_user' in request.POST:
            form = ProjectAddUserForm(request.POST)
            if form.is_valid():
                # try to add user
                try:
                    add_username = form.cleaned_data['username']
                    if project.add_user(add_username):
                        messages.success(request, 'User "%s" added to project!' % add_username)
                        form = ProjectAddUserForm()
                except:
                    logger.exception('Failed adding user')
                    form.add_error('username', '')
                    form.add_error('__all__', 'Unable to add user. Confirm that the username is correct.')
            else:
                form.add_error('__all__', 'There were errors processing your request. Please see below for details.')
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
                messages.error(request, 'An unexpected error occurred while attempting to remove this user. Please try again')

    else:
        form = ProjectAddUserForm()

    users = project.get_users()

    if not project_member_or_admin_or_superuser(request.user, project, users):
        raise PermissionDenied

    fg_migration = re.search(r'FG-(\d+)', project.chargeCode)
    if fg_migration:
        fg_project_num = fg_migration.group(1)
        fg_users = project_util.list_migration_users(fg_project_num)

        # filter out existing users
        fg_users = [u for u in fg_users if not any(x for x in users if x.username == u['username'])]
    else:
        fg_users = None

    project.has_active_allocations = False
    project.up_for_renewal = False

    # turn the allocation datetimes into actual datetimes for formatting purposes
    for a in project.allocations:
        a.start = datetime.strptime(a.start, '%Y-%m-%dT%H:%M:%SZ')
        a.end = datetime.strptime(a.end, '%Y-%m-%dT%H:%M:%SZ')

        print(a)

        # going to make a note here that setting this on the project object is probably short sighted
        # since it assumes projects will continue to only have one allocation. We can probably update this later.
        # Sorry future Carrie
        # Also note: 'Approved' shouldn't ever happen but the approval stuff isn't running in dev.
        if a.status == 'Pending' or a.status == 'Active' or a.status == 'Approved':
            project.has_active_allocations = True

        # if the allocation end is less than 3 months from now, show the renewal button
        three_months_to_end = a.end - timedelta(days=90)
        if datetime.today() > three_months_to_end:
            project.up_for_renewal = True

    return render(request, 'projects/view_project.html', {
        'project': project,
        'users': users,
        'is_pi': request.user.username == project.pi.username,
        'fg_migration': fg_migration,
        'fg_users': fg_users,
        'form': form,
    })

@login_required
def create_allocation(request, project_id, allocation_id = -1):
    tas = TASClient()

    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request, 'Only PI Eligible users can request allocations. If you would like to request PI Eligibility, please <a href="/user/profile/edit/">submit a PI Eligibility request</a>.')
        return HttpResponseRedirect(reverse('projects:user_projects'))

    project = Project.get(project_id)

    abstract = project.description.split("\n\n--- Supplemental details ---\n\n")
    justification = abstract[1].split("\n\n--- Funding source(s) ---\n\n")

    form = AllocationCreateForm(initial={'description': abstract[0],
                                         'supplemental_details': justification[0],
                                         'funding_source': justification[1]})

    if request.POST:
        if form.is_valid():
            allocation = form.cleaned_data.copy()
            allocation['computeRequested'] = '2000'
            # Also update the project
            allocation['justification'] = '%s\n\n--- Supplemental details ---\n\n%s\n\n--- Funding source(s) ---\n\n%s' % (allocation['description'], allocation['supplemental_details'], allocation['funding_source'])
            project['description'] = '%s\n\n--- Supplemental details ---\n\n%s\n\n--- Funding source(s) ---\n\n%s' % (allocation['description'], allocation['supplemental_details'], allocation['funding_source'])

            allocation.pop('description', None)
            allocation.pop('supplemental_details', None)
            allocation.pop('funding_source', None)

            allocation['projectId'] = project_id
            allocation['requestorId'] = tas.get_user(username=request.user)['id']
            allocation['resourceId'] = '39'

            if allocation_id > 0:
                allocation['id'] = allocation_id


            try:
                created_allocation = tas.create_allocation(allocation)
                updated_project = tas.edit_project(project)
                messages.success(request, 'Your allocation request has been submitted!')
                return HttpResponseRedirect(reverse('projects:view_project', args=[ updated_project['id'] ]))
            except:
                logger.exception('Error creating allocation')
                form.add_error('__all__', 'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__', 'There were errors processing your request. Please see below for details.')

    return render(request, 'projects/create_allocation.html', { 'form': form, 'project': project, 'alloc_id': allocation_id })

@login_required
@terms_required('project-terms')
def create_project(request):
    tas = TASClient()

    user = tas.get_user(username=request.user)
    if user['piEligibility'] != 'Eligible':
        messages.error(request, 'Only PI Eligible users can create new projects. If you would like to request PI Eligibility, please <a href="/user/profile/edit/">submit a PI Eligibility request</a>.')
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
            project['allocations'] = [
                {
                    'resourceId': 39,                        # chameleon
                    'requestorId': pi_user['id'],            # initial PI requestor
                    'justification': '--- Supplemental Details ---\n\n%s\n\n--- Funding Source(s) ---\n\n%s' % (project['supplemental_details'], project['funding_source']),# reuse for now
                    'computeRequested': 20000,               # simple request for now
                }
            ]

            project.pop('supplemental_details', None)
            project.pop('funding_source', None)

            # startup
            project['typeId'] = 2

            # source
            project['source'] = 'Chameleon'

            try:
                created_project = tas.create_project(project)
                messages.success(request, 'Your project has been created!')
                return HttpResponseRedirect(reverse('projects:view_project', args=[ created_project['id'] ]))
            except:
                logger.exception('Error creating project')
                form.add_error('__all__', 'An unexpected error occurred. Please try again')
        else:
            form.add_error('__all__', 'There were errors processing your request. Please see below for details.')

    else:
        form = ProjectCreateForm()

    return render(request, 'projects/create_project.html', { 'form': form })

@login_required
def edit_project(request):
    context = {}

    return render(request, 'projects/edit_project.html', context)

@login_required
def lookup_fg_projects(request):
    fg_projects = project_util.list_migration_projects(request.user.email)

    # filter already migrated projects
    tas = TASClient()
    projects = tas.projects_for_user(request.user)
    fg_projects = [p for p in fg_projects if not any(q for q in projects if q['chargeCode'] == 'FG-%s' % p.chargeCode) ]

    return render(request, 'projects/lookup_fg_project.html', { 'fg_projects': fg_projects })

@login_required
@terms_required('project-terms')
def fg_project_migrate(request, project_id):
    if request.method == 'POST':
        form = ProjectCreateForm(request.POST)
        tas = TASClient()
        try:
            pi_user = tas.get_user(username=request.user)

            # migrated data
            project = request.POST.copy()

            # default values
            project['chargeCode'] = 'FG-%s' % project_id
            project['typeId'] = 2 # startup
            project['piId'] = pi_user['id']

            # allocation
            project['allocations'] = [
                {
                    'resourceId': 39,                        # chameleon
                    'requestorId': pi_user['id'],            # initial PI requestor
                    'justification': 'FutureGrid project migration', # reuse for now
                    'computeRequested': 1,                   # simple request for now
                }
            ]

            # source
            project['source'] = 'Chameleon'

            logger.debug(project)

            created_project = tas.create_project(project)
            messages.success(request, 'Your project "%s" has been migrated to Chameleon!' % created_project['chargeCode'])
            return HttpResponseRedirect(reverse('projects:view_project', args=[ created_project['id'] ]))
        except Exception as e:
            logger.exception('Error migrating project')
            if len(e.args) > 1:
                if re.search('DuplicateProjectNameException', e.args[1]):
                    messages.error(request, 'A project with this name already exists. This project may have already been migrated.')
                else:
                    messages.error(request, 'An unexpected error occurred. Please try again')
            else:
                messages.error(request, 'An unexpected error occurred. Please try again')
    else:
        project = project_util.get_project(project_id)

        form = ProjectCreateForm(initial={
            'title': project.title,
            'description': project.abstract,
            'typeId': 2,
            'fieldId': 1,
        })

    form.fields['typeId'].widget = forms.HiddenInput()
    return render(request, 'projects/fg_project_migrate.html', { 'project': project, 'form': form })

@login_required
def fg_add_user(request, project_id):
    response = {}

    if request.POST:
        username = request.POST['username']
        email = request.POST['email']
        try:
            tas = TASClient()
            user = tas.get_user(username=username)
            if user['email'] == email:
                # add user to project
                if tas.add_project_user(project_id, username):
                    response['status'] = 'success'
                    response['message'] = 'User added to project!'
                    response['result'] = True
                else:
                    response['status'] = 'error'
                    response['message'] = 'An unexpected error occurred. Please try again.'
                    response['result'] = {
                        'error': 'unexpected_error'
                    }
            else:
                response['status'] = 'error'
                response['message'] = 'A user with this username exists, but the email is different. Please confirm that they are the same user (%s). You can add the user manually on the left.' % user['email']
                response['result'] = {
                    'error': 'user_email_mismatch'
                }
        except Exception as e:
            logger.exception('Error adding FG user to project')

            if e.args and e.args[0] == 'User not found':
                response['status'] = 'error'
                response['message'] = e.args[1]
                response['result'] = {
                    'error': 'user_not_found'
                }
            else:
                response['status'] = 'error'
                response['message'] = 'An unexpected error occurred. Please try again.'
                response['result'] = {
                    'error': 'unexpected_error'
                }

        return HttpResponse(json.dumps(response), content_type='application/json')
    else:
        return HttpResponseNotAllowed(['POST'])
