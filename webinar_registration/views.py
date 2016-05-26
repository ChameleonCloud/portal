from chameleon_token.decorators import token_required
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from . import forms, models
from datetime import datetime

def index(request):
    webinars = models.Webinar.objects.filter(registration_open__lte=datetime.now(), registration_closed__gte=datetime.now())

    if len(webinars) == 1:
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinars[0].id,)))

    return render(request, 'webinar_registration/index.html', {'webinars': webinars})

def webinar(request, id):
    webinar = models.Webinar.objects.get(id=id)

    # check if user has requested to participate
    try:
        participant = models.WebinarRegistrant.objects.get(webinar=webinar, user=request.user)
    except:
        participant = None


    return render(request, 'webinar_registration/webinar.html', {'webinar': webinar, 'participant': participant})

@login_required
def register(request, id):
    webinar = models.Webinar.objects.get(id=id)

    # Ensure program is accepting participants
    if not webinar.is_registration_open():
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))

    # Ensure that the user has not already requested to participate in this program.
    try:
        participant = models.WebinarRegistrant.objects.get(webinar=webinar, user=request.user)
    except:
        participant = None
    if participant:
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))

    context = { 'webinar': webinar, 'user' : request.user }

    if request.POST:
        form = forms.WebinarRegistrantForm(request.POST)
        if form.is_valid():
            join_request = form.save(commit=False)
            join_request.user = request.user
            join_request.webinar = webinar
            join_request.save()
            messages.success(request, 'You have been registered.')
            return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))
        context['form'] = form
    else:
        context['form'] = forms.WebinarRegistrantForm()


    return render(request, 'webinar_registration/register.html', context)

@token_required
def participants_export_list(request, id, list_type='uids'):
    """
    Returns a text file listing Early User Participants, one per line.
    """
    try:
        participants = models.WebinarRegistrant.objects.filter(webinar__id=id)
        if list_type == 'uids':
            content = list(p.user.username for p in participants)
        elif list_type == 'emails':
            content = list(p.user.email for p in participants)
        response = HttpResponse('\n'.join(content), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="webinar_%s_participants.txt"' % id
    except Exception as e:
        response = HttpResponse('Error: %s' % e)
        response.status_code = 400

    return response
