from chameleon_token.decorators import token_required
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from . import forms, models
from datetime import datetime

def index(request):
    programs = models.EarlyUserProgram.objects.exclude(state=models.PROGRAM_STATE__CLOSED)

    if len(programs) == 1:
        return HttpResponseRedirect(reverse('cc_early_user_support:program', args=(programs[0].id,)))

    return render(request, 'cc_early_user_support/index.html', {'programs': programs})

def view_program(request, id):
    program = models.EarlyUserProgram.objects.get(id=id)

    # check if user has requested to participate
    try:
        participant = models.EarlyUserParticipant.objects.get(program=program, user=request.user)
    except:
        participant = None


    return render(request, 'cc_early_user_support/view_program.html', {'program': program, 'participant': participant})

@login_required
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

@token_required
def participants_export_list(request, id, list_type='uids'):
    """
    Returns a text file listing Early User Participants, one per line.
    """
    try:
        participants = models.EarlyUserParticipant.objects.filter(program__id=id, participant_status=models.PARTICIPANT_STATUS__APPROVED)
        if list_type == 'uids':
            content = list(p.user.username for p in participants)
        elif list_type == 'emails':
            content = list(p.user.email for p in participants)
        response = HttpResponse('\n'.join(content), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="early_user_program_%s_participants.txt"' % id
    except Exception as e:
        response = HttpResponse('Error: %s' % e)
        response.status_code = 400

    return response
