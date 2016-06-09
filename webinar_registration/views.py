from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.mail import send_mail
from . import forms, models
#from datetime import datetime
from django.utils import timezone

def index(request):
    webinars = models.Webinar.objects.filter(end_date__gte=timezone.now())

    if len(webinars) == 1:
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinars[0].id,)))

    for w in webinars:
        try:
            p = models.WebinarRegistrant.objects.get(webinar=w, user=request.user)
            w.is_registered(True)
        except:
            p = None

    # TODO check if webinar is full

    return render(request, 'webinar_registration/index.html', {'webinars': webinars })

def webinar(request, id):
    webinar = models.Webinar.objects.get(id=id)

    # check if user has registered
    try:
        participant = models.WebinarRegistrant.objects.get(webinar=webinar, user=request.user)
    except:
        participant = None

    num_registrants = models.WebinarRegistrant.objects.filter(webinar=webinar).count()

    if webinar.registration_limit > 0:
        is_full = num_registrants  == webinar.registration_limit
    else:
        is_full = False

    return render(request, 'webinar_registration/webinar.html', {'webinar': webinar, 'participant': participant, 'is_full': is_full})

@login_required
def register(request, id):
    webinar = models.Webinar.objects.get(id=id)

    # Ensure program is accepting participants
    if not webinar.is_registration_open():
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))

    # Make sure the registration limit hasn't been reached yet
    num_registrants = models.WebinarRegistrant.objects.filter(webinar=webinar).count()

    if webinar.registration_limit > 0 and num_registrants == webinar.registration_limit:
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
            join_request.user = form.cleaned_data['user']
            join_request.webinar = form.cleaned_data['webinar']
            join_request.save()
            messages.success(request, 'You have been registered.')
            num_registrants = num_registrants + 1
            if num_registrants == webinar.registration_limit:
                send_mail('Registration limit reached for webinar ' + webinar.name,
                          'The registration limit for your webinar, ' + webinar.name + ', has been reached.',
                          'help@chameleoncloud.org',
                          ['help@chameleoncloud.org'], fail_silently=False)
            return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))
        context['form'] = form
    else:
        context['form'] = forms.WebinarRegistrantForm(initial={'user': request.user, 'webinar' : webinar})


    return render(request, 'webinar_registration/register.html', context)

@login_required
def unregister(request, id):
    webinar = models.Webinar.objects.get(id=id)
    try:
        participant = models.WebinarRegistrant.objects.get(webinar=webinar, user=request.user)
    except:
        participant = None
    if participant == None:
        return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))

    context = { 'webinar': webinar, 'user' : request.user }

    if request.POST:
        form = forms.WebinarRegistrantForm(request.POST)
        if form.is_valid():
            cancel_object = models.WebinarRegistrant.objects.get(user=form.cleaned_data['user'],webinar=form.cleaned_data['webinar'])
            cancel_object.delete()
            messages.success(request, 'You have cancelled your registration.')
            return HttpResponseRedirect(reverse('webinar_registration:webinar', args=(webinar.id,)))
        context['form'] = form
    else:
        context['form'] = forms.WebinarRegistrantForm(initial={'user': request.user, 'webinar' : webinar})


    return render(request, 'webinar_registration/unregister.html', context)
