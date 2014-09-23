from django.contrib.auth.models import User
from django.shortcuts import render
from django.views import generic


def futuregrid_activate(request):
    return render(request,"user/futuregrid_activate.html")

def profile(request):
    return render(request, 'user/profile.html')

# can't use this in menus.py
class UserView(generic.DetailView):
    model = User
    template_name = "user/profile.html"


def logged_out(request):
    return render(request, 'user/logged_out.html')


def register(request):
    return render(request, 'user/profile.html')
