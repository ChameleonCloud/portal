from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard( request ):
    actions = [
        { 'name': 'Manage your Projects', 'url': reverse( 'projects:user_projects' ) },
        { 'name': 'Help Desk Tickets', 'url': reverse( 'djangoRT:mytickets' ) },
        { 'name': 'Manage Your Account', 'url': reverse( 'tas:profile' ) },
    ]
    return render( request, 'dashboard.html', { 'actions': actions })
