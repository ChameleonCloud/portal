from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from pytas.pytas import client as TASClient
import json

@login_required
def profile( request ):
    context = {}

    try:
        tas = TASClient()
        resp = tas.get_user(username=request.user)
        context['profile'] = resp
    except:
        context['profile'] = False
        # raise Exception('error loading profile')

    return render(request, 'profile.html', context)

@login_required
def profile_edit( request ):
    context = {}

    tas = TASClient()
    try:
        resp = tas.get_user(username=request.user)
        context['profile'] = resp
    except:
        context['profile'] = False
        # raise Exception('error loading profile')

    try:
        inst = tas.institutions()
        context['institutions'] = inst

        curr_inst = next( ( x for x in inst if x['id'] == context['profile']['institutionId'] ), None)
        context['curr_inst'] = curr_inst
    except Exception as e:
        print e
        context['institutions'] = False


    try:
        countries = tas.countries()
        context['countries'] = countries
    except:
        context['countries'] = False

    return render(request, 'profile_edit.html', context)

def password_reset( request ):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'profile' ) )

    if request.POST:
        uname = request.POST['username']
        print uname
        if uname:
            messages.success(request, 'Your request has been received. If an account matching the username you provided is found, you will receive an email with further instructions to complete the password reset process.')
            return redirect( 'django.contrib.auth.views.login' )
        else:
            messages.error(request, 'Please provide your Chameleon Cloud Username')

    return render(request, 'password_reset.html')

def register( request ):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'profile' ) )

    context = {}
    tas = TASClient()
    try:
        inst = tas.institutions()
        context['institutions'] = inst

        # todo
        context['curr_inst'] = None
    except Exception as e:
        print e
        context['institutions'] = False

    try:
        countries = tas.countries()
        context['countries'] = countries
    except:
        context['countries'] = False

    return render(request, 'register.html', context)
