from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from datetime import datetime
from pytas.pytas import client as TASClient
from django.db import connections
from projectModel import Project

@login_required
def user_projects( request ):
    context = {}

    tas = TASClient()
    projects = tas.projects_for_user( request.user )

    ch_projects = []

    for p in projects:
        if p[ 'allocations' ]:
            # filter to just allocations with chameleon
            for a in p[ 'allocations' ]:
                if a[ 'resource' ] == 'Chameleon':
                    ch_projects.append( p )
                    break

        elif p[ 'chargeCode' ].startswith( 'FG-' ) or p[ 'chargeCode' ].startswith( 'CH-' ):
            ch_projects.append( p )


    context['projects'] = ch_projects

    return render( request, 'user_projects.html', context )

@login_required
def view_project( request, project_id ):

    tas = TASClient()
    project = tas.project( project_id )
    allocations = tas.project_allocations( project_id )

    return render( request, 'view_project.html', { 'project': project, 'allocations': allocations } )

@login_required
def create_project( request ):
    context = { 'form': {} }
    tas = TASClient()

    if request.method == 'POST':
        data = request.POST.copy()
        errors = {}

        if not data[ 'project_title' ]:
            errors[ 'project_title' ] = 'Please provide a project title'

        if not data[ 'abstract' ]:
            errors[ 'abstract' ] = 'Please provide a project abstract'

        if data[ 'project_type' ] == '-1':
            errors[ 'project_type' ] = 'Please select a project type'
        else:
            data[ 'project_type' ] = int( data[ 'project_type' ] )

        if data[ 'field_of_science' ]:
            data[ 'field_of_science' ] = int( data[ 'field_of_science' ] )
        else:
            errors[ 'field_of_science' ] = 'Please select a field of science'

        if len(errors) == 0:
            # success!
            try:
                pi_user = tas.get_user( username=request.user )

                data[ 'project_code' ] = 'CH-{0}'.format( datetime.now().microsecond )
                data[ 'pi_user_id' ] = pi_user[ 'id' ]
                print data

                project_id = tas.create_project(
                    data[ 'project_code' ],
                    data[ 'project_type' ],
                    data[ 'field_of_science' ],
                    data[ 'project_title' ],
                    data[ 'abstract' ],
                    data[ 'pi_user_id' ],
                )

                if project_id:
                    # hack to fix the project_code to be CH-{{project_id}}
                    tas.edit_project(
                        project_id,
                        'CH-{0}'.format(project_id),
                        data[ 'field_of_science' ],
                        data[ 'project_title' ],
                        data[ 'abstract' ],
                    )

                    tas.request_allocation(
                        data[ 'pi_user_id' ],
                        project_id,
                        39, # chameleon resource_id
                        data[ 'abstract' ], # reuse abstract as justification
                        1, # right now this is YES/NO
                    )
                    return HttpResponseRedirect( reverse( 'view_project', args=[ project_id ] ) )
                else:
                    # error
                    messages.error( request, 'An unexpected error occurred while creating your project request. Please try again.' )
            except Exception as e:
                print e
                messages.error( request, 'An unexpected error occurred while creating your project request. Please try again.' )

        context[ 'form' ][ 'data' ] = data
        context[ 'form' ][ 'errors' ] = errors
    else:
        context[ 'form' ][ 'data' ] = {}
        context[ 'form' ][ 'data' ][ 'field_of_science' ] = 3

    context[ 'fields' ] = tas.fields()

    return render( request, 'create_project.html', context )

@login_required
def edit_project( request ):
    context = {}

    return render( request, 'edit_project.html', context )

@login_required
def lookup_fg_projects( request ):
	cursor = connections['futuregrid'].cursor()

	cursor.execute("select name, node.title, ctfp.field_projectid_value, ctfp.field_project_abstract_value from users left join content_field_project_members cfpm on users.uid = cfpm.field_project_members_uid left join content_type_fg_projects ctfp on ctfp.nid = cfpm.nid left join node on node.nid = ctfp.nid where users.mail = %s", request.user.email)

	project = cursor.fetchall()

	projects = []

	for p in project:
		projects.append(Project(p[0], p[1], p[2], p[3]))

	context = { "projects" : projects }

	return render( request, 'lookup_fg_project.html', context)
