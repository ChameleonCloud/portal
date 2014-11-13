from django.shortcuts import render
from django.views import generic
from django.contrib.auth import authenticate, login
from django.core.urlresolvers import reverse

site = {
    "title": "Chameleon Cloud",
    "email": "contact@chameleoncloud.org",
    "description" : "Chameleon is a large-scale, reconfigurable experimental environment for next generation cloud research.",
    "baseurl": "/dev",
    "url": "http://www.chameleoncloud.org"
}

def home( request ):
    context = dict(site.items())
    return render(request, 'home.html', context)

def dashboard( request ):
    actions = []
    actions.append( { 'name': 'Manage your Projects', 'url': reverse( 'user_projects' ) } )
    actions.append( { 'name': 'Help Desk Tickets', 'url': reverse( 'mytickets' ) } )
    actions.append( { 'name': 'Manage Your Account', 'url': reverse( 'profile' ) } )
    return render( request, 'dashboard.html', { 'actions': actions })
