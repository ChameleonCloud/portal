from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from user_news.models import Outage
from djangoRT import rtUtil
from urlparse import urlparse
import logging
from pytas.models import Project
from webinar_registration.models import Webinar
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation
import sys
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required
def horizon_sso_login(request):
    next = ''
    ## first we get the url params, host and next
    next = request.GET.get('next') if request.GET.get('next') else ''
    host = request.GET.get('host')
    valid_callback_hosts = getattr(settings, 'SSO_CALLBACK_VALID_HOSTS', [])
    ## now, we verify the host is valid, if not valid, raise the alarm
    if not host or not host in valid_callback_hosts:
        logger.error('invalid or missing host in callback, host: ' + host)
        raise SuspiciousOperation("Invalid request")
    ## once we know the host is valid, we post the form
    context = {}
    context['sso_token'] = request.session['unscoped_token'].get('auth_token')
    protocol = 'http' if host.startswith('127.0.0.1') else 'https'
    context['host'] = protocol + '://' + host + '/auth/ccwebsso/' + '?next=' + next
    return render(request, 'sso/sso_callback_template.html', context)

@login_required
def dashboard(request):
    context = {}

    # active projects...
    projects = Project.list(username=request.user)
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
