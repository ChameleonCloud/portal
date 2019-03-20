from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from user_news.models import Outage
from djangoRT import rtUtil
from urlparse import urlparse
import logging
import chameleon.os_login as login
from tas import auth as tas_auth
from pytas.models import Project
from projects.models import ProjectExtras
from webinar_registration.models import Webinar
from django.utils import timezone
import sys
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)

@login_required
def horizon_sso_login(request):
    next = ''
    ## first we get the url params host, webroot, and next
    horizon_webroot = request.GET.get('webroot') if request.GET.get('webroot') else ''
    next = request.GET.get('next') if request.GET.get('next') else ''
    host = request.GET.get('host') if request.GET.get('host') else ''

    ## now we verify the host is valid, if not valid, log the error, send to home page...
    valid_callback_hosts = getattr(settings, 'SSO_CALLBACK_VALID_HOSTS', [])
    if not host or not host in valid_callback_hosts:
        logger.error('Invalid or missing host in callback by user ' \
            + request.user.username + ', callback host was: ' + host)
        return HttpResponseRedirect('/')

    ## get the Keystone token, and add to context 
    ## if none available, prompt user for username/password to get one
    context = {}
    try:
        context['sso_token'] = request.session['unscoped_token'].get('auth_token')
    except:
        return manual_ks_login(request)

    protocol = getattr(settings, 'SSO_CALLBACK_PROTOCOL', 'https')
    context['host'] = protocol + '://' + host + horizon_webroot + '/auth/ccwebsso/' + '?next=' + next
    return render(request, 'sso/sso_callback_template.html', context)

@login_required
def manual_ks_login(request):
    if request.method == 'POST':
        form = KSAuthForm(request, data=request.POST)
        user = None
        if request.user.username == request.POST.get('username') and form.is_valid():
            unscoped_token = login.get_unscoped_token(request)
            if unscoped_token:
                # We know login was successful!
                request.session['unscoped_token'] = unscoped_token
                return horizon_sso_login(request)
            else:
                return HttpResponseRedirect('/sso/horizon/unavailable')
        else:
            logger.error('an error occurred on horizon verify')
            form = KSAuthForm(request)
    else:
        form = KSAuthForm(request)

    context = {
        'form': form,
    }
    form.fields['username'].widget.attrs['readonly'] = True
    return render(request, 'sso/manual_ks_login.html', context)

## This page is meant for users who were trying to sso to Horizon, 
## but were unable to retrieve a Keystone token
@login_required
def horizon_sso_unavailable(request):
    """
    Here we're just checking to see if a keystone token is in the session,
    if it is, we shouldn't be here, let's redirect to the home page
    """
    if getattr(request.session, 'unscoped_token', None):
        return redirect('/')
    else:
        """
        If we're here we've tried to get a token from ks and failed,
        that means we can't log in to Horizon so we send them to a help page
        """
        return render(request, 'sso/keystone_login_unavailable.html', None)

class KSAuthForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        if request is not None:
            username = request.user.username
            initial = kwargs.get('initial', {})
            initial_default = {'username': username}
            initial_default.update(initial)
            kwargs['initial'] = initial_default
        super(KSAuthForm, self).__init__(request, *args, **kwargs)
    def clean_username(self):
        instance = getattr(self, 'instance', None)
        if instance:
            if instance.is_disabled:
                return instance.username
            else:
                return self.cleaned_data.get('username')

@login_required
def dashboard(request):
    context = {}

    # active projects...
    projects = Project.list(username=request.user)

    for proj in projects:
        try:
            extras = ProjectExtras.objects.get(tas_project_id=proj.id)
            proj.__dict__['nickname'] = extras.nickname
        except ProjectExtras.DoesNotExist:
            project_nickname = None


    context['active_projects'] = [p for p in projects \
                if p.source == 'Chameleon' and \
                any(a.status in ['Active', 'Approved', 'Pending'] for a in p.allocations)]

    # open tickets...
    rt = rtUtil.DjangoRt()
    context['open_tickets'] = rt.getUserTickets(request.user.email)

    # ongoing outages...
    outages = [o for o in Outage.objects.order_by('-end_date', '-start_date') if not o.resolved] # silly ORM quirk
    context['outages'] = outages

    webinars = Webinar.objects.filter(end_date__gte=timezone.now())
    context['webinars'] = webinars

    # federation status...
    if 'openid' in request.session:
        on_geni_project, on_chameleon_project = _check_geni_federation_status(request)
        context['geni_federation'] = {
            'on_geni_project': on_geni_project,
            'on_chameleon_project': on_chameleon_project,
            'geni_project_name': settings.GENI_FEDERATION_PROJECTS['geni']['name'],
            'chameleon_project_name': settings.GENI_FEDERATION_PROJECTS['chameleon']['name'],
        }

    return render(request, 'dashboard.html', context)

def _check_geni_federation_status(request):
    """
    Checks if a user who authenticated view GENI/OpenID is on the Chameleon Federation
    project on the GENI side. If so, then checks if the user is on the corresponding
    project on the Chameleon side.

    Returns a tuple of boolean values for (on_geni_project, on_chameleon_project)
    """

    geni_project_key = '%s|%s' % (settings.GENI_FEDERATION_PROJECTS['geni']['id'],
                                  settings.GENI_FEDERATION_PROJECTS['geni']['name'])

    on_geni_project = geni_project_key in request.session['openid']['ax']['projects']

    if on_geni_project:
        try:
            fed_proj = Project(settings.GENI_FEDERATION_PROJECTS['chameleon']['id'])
            on_chameleon_project = any(u.username == request.user.username \
                                        for u in fed_proj.get_users())
        except:
            logger.warn('Could not locate Chameleon federation project: %s' % \
                settings.GENI_FEDERATION_PROJECTS['chameleon'])
            on_chameleon_project = False
    else:
        on_chameleon_project = False

    return on_geni_project, on_chameleon_project
