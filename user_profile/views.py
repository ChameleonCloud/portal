from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from pytas.pytas import client as TASClient
import json

@login_required
def profile(request):
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
def profile_edit(request):
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
