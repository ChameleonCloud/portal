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
from projects.views import get_admin_ks_client as get_admin_ks_client
from webinar_registration.models import Webinar
from django.utils import timezone
from datetime import datetime
import sys
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from keystoneclient.v3 import client as ks_client
from keystoneauth1.identity import v3
from keystoneauth1 import session as ks_session
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

logger = logging.getLogger(__name__)

WHITELISTED_PROJECTS = ['openstack', 'maintenance']

@login_required
def horizon_sso_login(request):
    unscoped_token = request.session.get('unscoped_token')
    '''
    Because some users with previously active projects may be able to get auth tokens even if they can't access Horizon,
    we check with Keystone to verify an active project exists
    If user has an active project, we proceed to log them in

    Users who don't have active projects in Keystone are checked against TAS to see if they have approved projects, if they do
    we check the project start date and let them know when they can access Horizon
    '''
    active_ks_projects_found = False
    if unscoped_token:
        try:
            auth = v3.Token(auth_url=settings.OPENSTACK_KEYSTONE_URL, token=unscoped_token.get('auth_token'), project_id=None)
            sess = ks_session.Session(auth=auth, timeout=5)
            ks = ks_client.Client(session=sess)
            active_ks_projects_found = user_has_active_ks_project(ks, request.user)
            logger.debug('User: ' + request.user.username + ' is attempting to log in to Horizon; active_keystone_projects_found: ' + str(active_ks_projects_found))
        except Exception as e:
            ## if here, we have a token, but could not use it to connect to keystone so let's invalidate the token
            request.session['unscoped_token'] = None
            unscoped_token = None
            logger.error(e)
    if not active_ks_projects_found: # then check with TAS
        chameleon_projects = get_user_chameleon_projects(request.user)
        if chameleon_projects.get('approved_projects') and not chameleon_projects.get('active_projects'):
            earliest_start_date = None
            for p in chameleon_projects.get('approved_projects'):
                for a in p.allocations:
                    curr_alloc_date = datetime.strptime(a.start,'%Y-%m-%dT%H:%M:%SZ')
                    if earliest_start_date is None or curr_alloc_date < earliest_start_date:
                        earliest_start_date = curr_alloc_date
            # send users to a page that lets them know when their approved project begins
            logger.debug('User: ' + request.user.username + ' is attempting to log in to Horizon, approved project found in TAS but is not yet active, sending to informational page')
            return render(request, 'sso/chameleon_project_approved.html', {'active_date': datetime.strftime(earliest_start_date,'%B %d, %Y at %I:%M %p'),})
        else:
            '''
            If we're here the user has an active project in TAS but is either missing a token or the active projects in TAS don't exist in Keystone
            Failing to retrieve an unscoped token or projects from KS when the user has an active project in TAS may happen if the user's account is in a transient state so
            We give the user a chance to retrieve a token
            '''
            if not unscoped_token:
                return manual_ks_login(request)
    '''
    If we're here, then users have an active project and unscoped token, so we proceed to log them in to Horizon
    '''
    try:
        return redirect_to_horizon(request)
    except Exception as e:
        logger.error(e)
        return HttpResponseRedirect('/')

def redirect_to_horizon(request):
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

    protocol = getattr(settings, 'SSO_CALLBACK_PROTOCOL', 'https')
    context = {}
    context['sso_token'] = request.session.get('unscoped_token').get('auth_token')
    context['host'] = protocol + '://' + host + horizon_webroot + '/auth/ccwebsso/' + '?next=' + next
    return render(request, 'sso/sso_callback_template.html', context)

def sync_user_project_status(ks, username):
    admin_ks_client = get_admin_ks_client()
    ks_projects = ks.federation.projects.list()
    chameleon_projects = get_user_chameleon_projects(username)
    active_tas_projects = chameleon_projects.get('active_projects')
    active_tas_charge_codes = list(p.chargeCode for p in active_tas_projects)
    logger.debug('*** List of active charge codes in tas' + str(active_tas_charge_codes))
    if ks_projects:
        for ks_p in ks_projects:
            charge_code = ks_p.charge_code
            if charge_code in WHITELISTED_PROJECTS:
                logger.debug('Ignoring project with charge code {}'.format(charge_code))
                continue
            logger.debug('Keystone charge code: ' + charge_code)
            if charge_code in active_tas_charge_codes and not ks_p.enabled:
                admin_ks_client.projects.update(ks_p, enabled = True)
            elif not charge_code in active_tas_charge_codes and ks_p.enabled:
                admin_ks_client.projects.update(ks_p, enabled = False)

def user_has_active_ks_project(ks, user):
    sync_user_project_status(ks, user)
    ks_projects = ks.federation.projects.list()
    for p in ks_projects:
        if p.enabled:
            return True
    return False

def get_user_chameleon_projects(user):
    tas_projects = Project.list(username=user)
    chameleon_projects = {}
    active_projects = [p for p in tas_projects \
                if p.source == 'Chameleon' and \
                (a.status in ['Active'] for a in p.allocations)]
    approved_projects = [p for p in tas_projects \
                if p.source == 'Chameleon' and \
                (a.status in ['Approved'] for a in p.allocations)]
    pending_projects = [p for p in tas_projects \
                if p.source == 'Chameleon' and \
                (a.status in ['Pending'] for a in p.allocations)]

    chameleon_projects['active_projects'] = active_projects
    chameleon_projects['approved_projects'] = approved_projects
    chameleon_projects['pending_projects'] = pending_projects
    return chameleon_projects

@login_required
@sensitive_post_parameters()
@csrf_protect
@never_cache
def manual_ks_login(request):
    if request.method == 'POST':
        form = KSAuthForm(request, data=request.POST)
        user = None
        unscoped_token = None
        if request.user.username == request.POST.get('username') and form.is_valid():
            tbe = tas_auth.TASBackend()
            try:
                user = tbe.authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
            except Exception as e:
                form.add_error('password', 'Invalid password')
                logger.error('Invalid password when attempting to retrieve token : {}'.format(request.user.username + ', ' + e.message) + str(sys.exc_info()[0]))
        else:
            logger.error('An error occurred on form validation for user ' + request.user.username)

        #if tas auth returned a user, the credentials were valid, let's get a token
        if user:
            unscoped_token = login.get_unscoped_token(request)
            if unscoped_token:
                logger.info('User: ' + request.user.username + ' retrieved unscoped token successfully via manual_ks_login form.')
                request.session['unscoped_token'] = unscoped_token
                return horizon_sso_login(request)
            else:
                logger.info('User: ' + request.user.username + ' could not retrieve unscoped token via manual_ks_login form.')
                return HttpResponseRedirect('/sso/horizon/unavailable')

    form = KSAuthForm(request)
    context = {
        'form': form,
    }
    form.fields['username'].widget.attrs['readonly'] = True
    return render(request, 'sso/manual_ks_login.html', context)


@login_required
def horizon_sso_unavailable(request):
    #     """
    #     If we're here we've tried to get a token from ks and failed,
    #     that means we can't log in to Horizon so we send them to a help page
    #     """
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
