from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from pytas.pytas import client as TASClient

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

        elif p[ 'name' ].startswith( 'FG-' ) or p[ 'name' ].startswith( 'CH-' ):
            ch_projects.append( p )


    context['projects'] = ch_projects

    return render( request, 'user_projects.html', context )

@login_required
def view_project( request ):
    context = {}

    return render( request, 'view_project.html', context )

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
