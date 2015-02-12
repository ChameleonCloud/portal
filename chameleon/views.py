from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views import generic
from django.contrib.auth.decorators import login_required
from github_content import util as content_util
from datetime import datetime
from django.contrib import messages

site = {
    "title": "Chameleon Cloud",
    "email": "contact@chameleoncloud.org",
    "description" : "Chameleon is a large-scale, reconfigurable experimental environment for next generation cloud research.",
    "url": "http://www.chameleoncloud.org"
}

def _maintenance_message( request ):
    endtime = datetime(2015, 02, 18, 00, 00)
    if datetime.now() < endtime:
        message = '<h4>{0}</h4><p><b>{1}</b></p>{2}'.format(
            'OpenStack Maintenance on Alamo',
            'Tuesday, February 17 8:00 CST - 18:00 CST',
            'We will be enhancing our OpenStack deployment on Alamo and users may experience brief outages during this time. We expect that the outages will be intermittent, so we currently plan to let users continue to use Alamo during this time.'
        )
        messages.info( request, message )

def home( request ):
    _maintenance_message( request )
    context = dict(site.items())
    posts = content_util.get_posts( limit=2 )
    context['posts'] = posts
    return render(request, 'home.html', context)

@login_required
def dashboard( request ):
    _maintenance_message( request )
    actions = []
    actions.append( { 'name': 'Manage your Projects', 'url': reverse( 'user_projects' ) } )
    actions.append( { 'name': 'Help Desk Tickets', 'url': reverse( 'mytickets' ) } )
    actions.append( { 'name': 'Manage Your Account', 'url': reverse( 'profile' ) } )
    return render( request, 'dashboard.html', { 'actions': actions })

def newsletter( request ):
    return render( request, 'newsletter.html' )
