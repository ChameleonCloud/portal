from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from datetime import datetime
from pytas.pytas import client as TASClient
from django.db import connections
from projectModel import Project
from forms import ProjectCreateForm, ProjectAddUserForm
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
        if p[ 'source' ] == 'Chameleon':
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
                    if tas.add_project_user( project_id, form.cleaned_data['username'] ):
                        form = ProjectAddUserForm()
                        messages.success( request, 'User "%s" added to project!' % form.cleaned_data['username'] )
                except:
                    logger.exception( 'Failed adding user' )
                    form.add_error( 'username', '' )
                    form.add_error( '__all__', 'Unable to add user. Confirm that the username is correct.' )
        else:
            form = ProjectAddUserForm()

        if 'del_user' in request.POST:
            # try to remove user
            try:
                if tas.del_project_user( project_id, request.POST['username'] ):
                    messages.success( request, 'User "%s" removed from project' % request.POST['username'] )
            except:
                logger.exception( 'Failed removing user' )
                messages.error( request, 'An unexpected error occurred while attempting to remove this user. Please try again' )

    else:
        form = ProjectAddUserForm()

    project = tas.project( project_id )
    users = tas.get_project_users( project_id )

    return render( request, 'view_project.html', {
        'project': project,
        'users': users,
        'is_pi': request.user.username == project['pi']['username'],
        'form': form,
    } )

@login_required
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
                # print json.dumps( created_project )
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
    cursor = connections['futuregrid'].cursor()

    cursor.execute("select name, node.title, ctfp.field_projectid_value, ctfp.field_project_abstract_value from users left join content_field_project_members cfpm on users.uid = cfpm.field_project_members_uid left join content_type_fg_projects ctfp on ctfp.nid = cfpm.nid left join node on node.nid = ctfp.nid where users.mail = %s", [request.user.email])

    project = cursor.fetchall()

    projects = []

    for p in project:
        projects.append(Project(p[0], p[1], p[2], p[3]))

    context = { "projects" : projects }

    return render( request, 'lookup_fg_project.html', context)

def fg_project_migrate( request ):
    if request.method == 'POST':
        try:
            pi_user = tas.get_user( username=request.user )
            project_id = tas.create_project(
                request.POST['project_code'],
                2, # startup
                1, # not chosen
                request.POST['project_title'],
                request.POST['abstract'],
                pi_user['id'],
            )

            if project_id:
                tas.request_allocation(
                    pi_user['id'],
                    project_id,
                    39, # chameleon resource_id
                    request.POST[ 'abstract' ], # reuse abstract as justification
                    1, # right now this is YES/NO
                )
                messages.success( request, 'Your project {0} has been migrated to Chameleon!' )
                return HttpResponseRedirect( reverse( 'view_project', args=[ project_id ] ) )
            else:
                messages.error( request, 'An unexpected error occurred while creating your project request. Please try again.' )
        except Exception as e:
            logger.error(e)
            messages.error( request, 'An unexpected error occurred while creating your project request. Please try again.' )
    return HttpResponseRedirect( reverse( 'lookup_fg_projects' ) )
