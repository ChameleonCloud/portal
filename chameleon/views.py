from django.shortcuts import render
from django.views import generic
from django.contrib.auth import authenticate, login

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
    context = {}
    return render( request, 'dashboard.html', context)
