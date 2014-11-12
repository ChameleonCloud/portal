from django.shortcuts import render

# Create your views here.
def user_projects( request ):
    context = {}

    return render( request, 'user_projects.html', context )

def view_project( request ):
    context = {}

    return render( request, 'view_project.html', context )

def edit_project( request ):
    context = {}

    return render( request, 'edit_project.html', context )
