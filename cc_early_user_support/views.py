from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from . import forms, models
from datetime import datetime

def index(request):
    programs = models.EarlyUserProgram.objects.exclude(state=models.PROGRAM_STATE__CLOSED)

    # check if user has requested to participate

    return render(request, 'cc_early_user_support/index.html', {'programs': programs})

def view_program(request, id):
    program = models.EarlyUserProgram.objects.get(id=id)

    # check if user has requested to participate
    try:
        participant = models.EarlyUserParticipant.objects.get(program=program, user=request.user)
    except:
        participant = None


    return render(request, 'cc_early_user_support/view_program.html', {'program': program, 'participant': participant})

def request_to_participate(request, id):
    program = models.EarlyUserProgram.objects.get(id=id)

    # Ensure program is accepting participants
    if not program.is_open():
        return HttpResponseRedirect(reverse('cc_early_user_support:program', args=(program.id,)))

    # Ensure that the user has not already requested to participate in this program.
    try:
        participant = models.EarlyUserParticipant.objects.get(program=program, user=request.user)
    except:
        participant = None
    if participant:
        return HttpResponseRedirect(reverse('cc_early_user_support:program', args=(program.id,)))

    context = { 'program': program }

    if request.POST:
        form = forms.EarlyUserParticipantForm(request.POST)
        if form.is_valid():
            join_request = form.save(commit=False)
            join_request.user = request.user
            join_request.program = program
            join_request.save()
            messages.success(request, 'Your request has been received.')
            return HttpResponseRedirect(reverse('cc_early_user_support:program', args=(program.id,)))
        context['form'] = form
    else:
        context['form'] = forms.EarlyUserParticipantForm()


    return render(request, 'cc_early_user_support/request_to_participate.html', context)
