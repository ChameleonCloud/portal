from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views import generic
from django.contrib.auth.decorators import login_required
from github_content import util as content_util

site = {
    "title": "Chameleon Cloud",
    "email": "contact@chameleoncloud.org",
    "description" : "Chameleon is a large-scale, reconfigurable experimental environment for next generation cloud research.",
    "url": "http://www.chameleoncloud.org"
}

def home( request ):
    context = dict(site.items())

    posts = content_util.get_posts( limit=2 )
    context['posts'] = posts

    return render(request, 'home.html', context)

@login_required
def dashboard( request ):
    actions = []
    actions.append( { 'name': 'Manage your Projects', 'url': reverse( 'user_projects' ) } )
    actions.append( { 'name': 'Help Desk Tickets', 'url': reverse( 'mytickets' ) } )
    actions.append( { 'name': 'Manage Your Account', 'url': reverse( 'profile' ) } )
    return render( request, 'dashboard.html', { 'actions': actions })

def newsletter( request ):
    return render( request, 'newsletter.html' )
