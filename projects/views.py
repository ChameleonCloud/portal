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

    query_str = """SELECT DISTINCT
                u.name,
                n.title,
                p.field_projectid_value,
                p.field_project_abstract_value,
                manager.mail AS manager,
                lead.mail AS lead,
                u.uid = lead.uid OR u.uid = manager.uid AS is_pi
                FROM node n
                LEFT JOIN content_type_fg_projects p on p.nid = n.nid
                LEFT JOIN content_field_project_members mem ON mem.nid = n.nid
                LEFT JOIN users manager on manager.uid = p.field_project_manager_uid
                LEFT JOIN users lead on lead.uid = p.field_project_lead_uid
                LEFT JOIN users member ON mem.field_project_members_uid = member.uid
                LEFT JOIN users u on u.uid = member.uid OR u.uid = lead.uid OR u.uid = manager.uid
                WHERE n.type = 'fg_projects'
                AND u.mail = %s"""

    # cursor.execute(query_str, [request.user.email])
    cursor.execute(query_str, ['priteau@uchicago.edu'])

    project = cursor.fetchall()

    projects = []

    for p in project:
        projects.append(Project(p[0], p[1], p[2], p[3], p[4], p[5], p[6]))

    context = { "projects" : projects }

    return render( request, 'lookup_fg_project.html', context)

def fg_project_migrate( request ):
    if request.method == 'POST':
        try:
            pi_user = tas.get_user( username=request.user )
            project = request.POST.copy()
            project['typeId'] = 2 # startup
            project['fieldId'] = 1 # not chosen
            project['piId'] = pi_user['id']
            project['allocations'] = [
                {
                    'resourceId': 39,                        # chameleon
                    'requestorId': pi_user['id'],            # initial PI requestor
                    'justification': 'FutureGrid migration', # reuse for now
                    'computeRequested': 1,                   # simple request for now
                }
            ]

            created_project = tas.create_project( project )
            messages.success( request, 'Your project "%s" has been migrated to Chameleon!' % created_project['name'] )
            return HttpResponseRedirect( reverse( 'view_project', args=[ created_project['id'] ] ) )
        except:
            logger.exception( 'Error migrating project' )
            messages.error( request, 'An unexpected error occurred. Please try again' )
    return HttpResponseRedirect( reverse( 'lookup_fg_projects' ) )
