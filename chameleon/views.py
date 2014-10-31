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

def home(request):

    print("**** authenticated: %s" % request.user.is_authenticated())
    print("%s" % request.user)

    context = dict(site.items())

    return render(request, 'home.html', context)

def login(request):
    context = {}

    data = request.POST
    if data:
        
        authenticate(username=data['username'], password=data['password'])
        context['username'] = data['username']

    return render(request, 'login.html', context)
