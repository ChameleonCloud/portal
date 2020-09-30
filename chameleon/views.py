from functools import wraps
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from user_news.models import Outage
from djangoRT import rtUtil
from urllib.parse import urlparse
import logging
import chameleon.os_login as login
from tas import auth as tas_auth
from webinar_registration.models import Webinar
from django.utils import timezone
from datetime import datetime
import sys
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from keystoneclient.v3 import client as ks_client
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from chameleon.keystone_auth import admin_ks_client, sync_projects, sync_user, get_user, regenerate_tokens, get_token, has_valid_token
from util.project_allocation_mapper import ProjectAllocationMapper

logger = logging.getLogger(__name__)


def set_services_region(view_func):
    """A decorator that sets the services region on the session object.

    This is available as a decorator as it may need to occur before other
    decorators, like login_required, in order to ensure that any Keystone
    operations that take place during login have access to this.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        services_region = request.GET.get('services_region')
        if services_region:
            request.session['services_region'] = services_region
        elif request.GET.get('host') == 'kvm.tacc.chameleoncloud.org':
            request.session['services_region'] = 'CHI@TACC'
        return view_func(request, *args, **kwargs)
    return wrapper


@set_services_region
@login_required
def horizon_sso_login(request):
    '''
    Because some users with previously active projects may be able to get auth
    tokens even if they can't access Horizon, we check with Keystone to verify
    an active project exists. If user has an active project, we proceed to log
    them in

    Users who don't have active projects in Keystone are checked against TAS to
    see if they have approved projects, if they do we check the project start
    date and let them know when they can access Horizon.
    '''
    username = request.user.username
    mapper = ProjectAllocationMapper(request)
    user_projects = mapper.get_user_projects(username, to_pytas_model=True)
    active_projects = [
        p for p in user_projects
        if any(a.status == 'Active' for a in p.allocations)
    ]
    approved_projects = [
        p for p in user_projects
        if any(a.status == 'Approved' for a in p.allocations)
    ]
    ks_admin = admin_ks_client(request=request)
    ks_user = get_user(ks_admin, username)
    if not ks_user:
        logger.info((
            'User {} attempting SSO but does not exist in Keystone, forcing '
            'manual login'.format(username)))
        return manual_ks_login(request)

    ks_projects = sync_projects(ks_admin, ks_user, active_projects)

    if not has_valid_token(request):
        if len([k for k in ks_projects if k.enabled]) > 0:
            '''
            If we're here the user has an active project in TAS but is either
            missing a token or the active projects in TAS don't exist in
            Keystone. Failing to retrieve an unscoped token or projects from KS
            when the user has an active project in TAS may happen if the user's
            account is in a transient state so we give the user a chance to
            retrieve a token.
            '''
            logger.info((
                'User {} attempting SSO, active keystone projects found, but '
                'no auth token in session, trying manual ks login.'
                .format(username)))
            return manual_ks_login(request)
        else:
            if approved_projects and not active_projects:
                earliest_start_date = None
                for p in approved_projects:
                    for a in p.allocations:
                        curr_alloc_date = datetime.strptime(a.start,'%Y-%m-%dT%H:%M:%SZ')
                        if earliest_start_date is None or curr_alloc_date < earliest_start_date:
                            earliest_start_date = curr_alloc_date
                # send users to a page that lets them know when their approved project begins
                logger.debug('User: {} is attempting to log in to Horizon, approved project found in TAS but is not yet active, sending to informational page'.format(username))
                return render(request, 'sso/chameleon_project_approved.html', {
                    'active_date': datetime.strftime(earliest_start_date,'%B %d, %Y at %I:%M %p')
                })
            else:
                return horizon_sso_unavailable(request)

    '''
    If we're here, then users have an active project and unscoped token, so we
    proceed to log them in to Horizon
    '''
    try:
        return redirect_to_horizon(request)
    except Exception as e:
        logger.error(e)
        return HttpResponseRedirect('/')

def redirect_to_horizon(request):
    horizon_webroot = request.GET.get('webroot') or ''
    next = request.GET.get('next') or ''
    host = request.GET.get('host') or ''

    ## now we verify the host is valid, if not valid, log the error, send to home page...
    valid_callback_hosts = getattr(settings, 'SSO_CALLBACK_VALID_HOSTS', [])
    if not host or not host in valid_callback_hosts:
        logger.error('Invalid or missing host in callback by user ' \
            + request.user.username + ', callback host was: ' + host)
        return HttpResponseRedirect('/')

    protocol = getattr(settings, 'SSO_CALLBACK_PROTOCOL', 'https')
    context = {}
    context['sso_token'] = get_token(request)
    context['host'] = protocol + '://' + host + horizon_webroot + '/auth/websso/' + '?next=' + next
    return render(request, 'sso/sso_callback_template.html', context)

@login_required
@sensitive_post_parameters()
@csrf_protect
@never_cache
def manual_ks_login(request):
    if request.method == 'POST':
        form = KSAuthForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        tas_user = None
        if request.user.username == username and form.is_valid():
            tbe = tas_auth.TASBackend()
            try:
                tas_user = tbe.authenticate(username=username, password=password)
            except Exception as e:
                form.add_error('password', 'Invalid password')
                logger.error('Invalid password when attempting to retrieve token : {}'.format(username + ', ' + e.message) + str(sys.exc_info()[0]))
        else:
            logger.error('An error occurred on form validation for user ' + request.user.username)

        # if tas auth returned a user, the credentials were valid
        if tas_user:
            regenerate_tokens(request, password)
            # Check if we were able to generate a token for the region the
            # user is trying to log in to
            if has_valid_token(request):
                logger.info((
                    'User {} retrieved unscoped token successfully via manual '
                    'form.'.format(username)))
                return horizon_sso_login(request)
            else:
                logger.info((
                    'User {} could not retrieve unscoped token via manual '
                    'form.'.format(username)))
                return HttpResponseRedirect('/sso/horizon/unavailable')

    form = KSAuthForm(request)
    context = {
        'form': form,
    }
    form.fields['username'].widget.attrs['readonly'] = True
    return render(request, 'sso/manual_ks_login.html', context)


@login_required
def horizon_sso_unavailable(request):
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
    mapper = ProjectAllocationMapper(request)
    active_projects = mapper.get_user_projects(request.user.username,
        alloc_status=['Active', 'Approved', 'Pending'], to_pytas_model=True)
    context['active_projects'] = active_projects

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


def new_login_experience(request):
    opt_in = 'opt-out' not in request.GET
    cookie_name = settings.NEW_LOGIN_EXPERIENCE_COOKIE
    is_opted_in = request.COOKIES.get(cookie_name) == '1'
    response = HttpResponseRedirect('/')

    hostname = request.get_host().split(':')[0]
    # Grab root level domain (TLD + zone)
    root_domain = '.{}'.format('.'.join(hostname.split('.')[-2:]))

    if (not is_opted_in) and opt_in:
        if request.user.is_authenticated():
            # Also log out the user
            response = HttpResponseRedirect(reverse('logout'))
        one_year_s = 60 * 60 * 24 * 365
        # Set cookie on all subdomains off of the root. This allows
        # any application deployed on the root domain to read this value.
        response.set_cookie(cookie_name, '1', domain=root_domain,
            max_age=one_year_s, httponly=True)
        messages.info(request, 'You have been opted in to the new login experience.')
    elif is_opted_in and (not opt_in):
        if request.user.is_authenticated():
            # Also log out the user
            response = HttpResponseRedirect(reverse('logout'))
        response.delete_cookie(cookie_name, domain=root_domain)
        messages.info(request, 'You have been opted out of the new login experience.')
    else:
        messages.info(request, 'Your opt-in status has not changed.')
    return response


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
            on_chameleon_project = ProjectAllocationMapper.is_geni_user_on_chameleon_project(request.user.username)
        except:
            logger.warn('Could not locate Chameleon federation project: %s' % \
                settings.GENI_FEDERATION_PROJECTS['chameleon'])
            on_chameleon_project = False
    else:
        on_chameleon_project = False

    return on_geni_project, on_chameleon_project
