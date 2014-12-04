from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from chameleon.decorators import terms_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from datetime import datetime
from pytas.pytas import client as TASClient
from forms import ProjectCreateForm, ProjectAddUserForm
import project_util
import re
import logging
import json

logger = logging.getLogger('default')

@login_required
def user_projects( request ):
    context = {}

    tas = TASClient()
    projects = tas.projects_for_user( request.user )

    ch_projects = []

    for p in projects:
        if 'source' in p and p[ 'source' ] == 'Chameleon':
            ch_projects.append( p )

    context['projects'] = ch_projects

    return render( request, 'user_projects.html', context )

@login_required
def view_project( request, project_id ):
    tas = TASClient()

    if request.POST:
        if 'add_user' in request.POST:
            form = ProjectAddUserForm( request.POST )
            if form.is_valid():
                # try to add user
                try:
                    add_username = form.cleaned_data['username']
                    if tas.add_project_user( project_id, add_username ):
                        messages.success( request, 'User "%s" added to project!' % add_username )
                        form = ProjectAddUserForm()
                except:
                    logger.exception( 'Failed adding user' )
                    form.add_error( 'username', '' )
                    form.add_error( '__all__', 'Unable to add user. Confirm that the username is correct.' )
        else:
            form = ProjectAddUserForm()

        if 'del_user' in request.POST:
            # try to remove user
            try:
                del_username = request.POST['username']
                if tas.del_project_user( project_id, del_username ):
                    messages.success( request, 'User "%s" removed from project' % del_username )
            except:
                logger.exception( 'Failed removing user' )
                messages.error( request, 'An unexpected error occurred while attempting to remove this user. Please try again' )

    else:
        form = ProjectAddUserForm()

    project = tas.project( project_id )
    users = tas.get_project_users( project_id )
    fg_migration = re.search( r'FG-(\d+)', project['chargeCode'] )
    if fg_migration:
        fg_project_num = fg_migration.group( 1 )
        fg_users = project_util.list_migration_users( fg_project_num )

        # filter out existing users
        fg_users = [u for u in fg_users if not any( x for x in users if x['username'] == u['username'] ) ]
    else:
        fg_users = None

    return render( request, 'view_project.html', {
        'project': project,
        'users': users,
        'is_pi': request.user.username == project['pi']['username'],
        'fg_migration': fg_migration,
        'fg_users': fg_users,
        'form': form,
    } )

@login_required
@terms_required('project-terms')
def create_project( request ):
    tas = TASClient()

    if request.POST:
        form = ProjectCreateForm( request.POST )
        if form.is_valid():
            # title, description, typeId, fieldId
            project = form.cleaned_data.copy()

            # pi
            pi_user = tas.get_user( username=request.user )
            project['piId'] = pi_user['id']

            # allocations
            project['allocations'] = [
                {
                    'resourceId': 39,                        # chameleon
                    'requestorId': pi_user['id'],            # initial PI requestor
                    'justification': 'Initial; see abstract',# reuse for now
                    'computeRequested': 1,                   # simple request for now
                }
            ]

            # source
            project['source'] = 'Chameleon'

            try:
                created_project = tas.create_project( project )
                messages.success( request, 'Your project has been created!' )
                return HttpResponseRedirect( reverse( 'view_project', args=[ created_project['id'] ] ) )
            except:
                logger.exception( 'Error creating project' )
                form.add_error('__all__', 'An unexpected error occurred. Please try again')

    else:
        form = ProjectCreateForm()

    return render( request, 'create_project.html', { 'form': form } )

@login_required
def edit_project( request ):
    context = {}

    return render( request, 'edit_project.html', context )

@login_required
def lookup_fg_projects( request ):
    fg_projects = project_util.list_migration_projects( request.user.email )

    # filter already migrated projects
    tas = TASClient()
    projects = tas.projects_for_user( request.user )
    fg_projects = [p for p in fg_projects if not any( q for q in projects if q['chargeCode'] == 'FG-%s' % p.chargeCode ) ]

    return render( request, 'lookup_fg_project.html', { 'fg_projects': fg_projects } )

@login_required
def fg_project_confirm( request ):
    postData = request.POST.copy()

    if request.POST and 'chargeCode' in postData:
        project = project_util.get_project(postData['chargeCode'])
        form = ProjectCreateForm( request.POST )
    else:
        project = {}
        form = ProjectCreateForm()


    return render( request, 'confirm_fg_project.html', { 'project': project, 'form': form } )

@login_required
@terms_required('project-terms')
def fg_project_migrate( request ):
    if request.method == 'POST':
        tas = TASClient()
        try:
            pi_user = tas.get_user( username=request.user )

            # migrated data
            project = request.POST.copy()

            # default values
            project['typeId'] = 2 # startup
            project['fieldId'] = 1 # not chosen
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

            logger.debug( project )

            created_project = tas.create_project( project )
            messages.success( request, 'Your project "%s" has been migrated to Chameleon!' % created_project['chargeCode'] )
            return HttpResponseRedirect( reverse( 'view_project', args=[ created_project['id'] ] ) )
        except:
            logger.exception( 'Error migrating project' )
            messages.error( request, 'An unexpected error occurred. Please try again' )
    return HttpResponseRedirect( reverse( 'lookup_fg_projects' ) )

@login_required
def fg_add_user( request, project_id ):
    response = {}

    if request.POST:
        username = request.POST['username']
        email = request.POST['email']
        try:
            tas = TASClient()
            user = tas.get_user( username=username )
            if user['email'] == email:
                # add user to project
                if tas.add_project_user( project_id, username ):
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
            logger.exception( 'Error adding FG user to project' )

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

        return HttpResponse( json.dumps( response ), content_type='application/json' )
    else:
        return HttpResponseNotAllowed( ['POST'] )
