from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
from django.forms.util import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render

import logging
import re

from openid.consumer import consumer
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import ax, pape, sreg
from openid.store.filestore import FileOpenIDStore

from .models import OpenIDUserIdentity
from .utils import JSONSafeSession, DBOpenIDStore

from chameleon.decorators import anonymous_required
from tas.forms import UserRegistrationForm
from tas.views import _clean_registration_data


logger = logging.getLogger(__name__)

def _get_openid_store():
    return DBOpenIDStore()


def _get_consumer(request):
    return consumer.Consumer(JSONSafeSession(request.session), _get_openid_store())


@anonymous_required
def openid_login(request):
    if request.method == 'POST':
        openid_url = request.POST.get('openid_url')
        logger.debug('Attempting OpenID login at %s' % openid_url)
        c = _get_consumer(request)
        try:
            auth_request = c.begin(openid_url)

            sreg_request = sreg.SRegRequest(required=['email', 'nickname'],)
            auth_request.addExtension(sreg_request)

            ax_request = ax.FetchRequest()
            ax_request.add(ax.AttrInfo('http://geni.net/projects',
                                       required=False,
                                       count=ax.UNLIMITED_VALUES))
            ax_request.add(ax.AttrInfo('http://geni.net/user/prettyname', required=False))
            auth_request.addExtension(ax_request)

            trust_root = request.build_absolute_uri(reverse('chameleon_openid:openid_login'))
            return_to = request.build_absolute_uri(reverse('chameleon_openid:openid_callback'))
            url = auth_request.redirectURL(trust_root, return_to)
            return HttpResponseRedirect(url)

        except DiscoveryFailure, e:
            logger.error("OpenID discovery error: %s" % (str(e),))

    return render(request, 'chameleon_openid/login.html')


@anonymous_required
def openid_callback(request):

    request_args = dict(request.GET.items())
    if request.method == 'POST':
        request_args = dict(request.POST.items())

    if request_args:
        c = _get_consumer(request)
        return_to = request.build_absolute_uri(reverse('chameleon_openid:openid_callback'))
        response = c.complete(request_args, return_to)

        sreg_response = {}
        ax_items = {}
        if response.status == consumer.SUCCESS:
            sreg_response = sreg.SRegResponse.fromSuccessResponse(response)

            ax_response = ax.FetchResponse.fromSuccessResponse(response)
            if ax_response:
                ax_items = {
                    'projects': ax_response.get('http://geni.net/projects'),
                    'full_name': ax_response.get('http://geni.net/user/prettyname'),
                }


            result = {}
            result['status'] = response.status
            result['url'] = response.getDisplayIdentifier()
            result['sreg'] = sreg_response and dict(sreg_response.items())
            result['ax'] = ax_items
            request.session['openid'] = result

            user = authenticate(openid_identity=result['url'])
            if user:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'Login success using OpenID.')
                    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
                else:
                    messages.error(request, 'Your account is not active yet. Please confirm your email address before logging in.')
                    return HttpResponseRedirect('/')
            else:
                return HttpResponseRedirect(reverse('chameleon_openid:openid_connect'))

        elif response.status == consumer.CANCEL:
            messages.warning(request, 'OpenID authentication cancelled by user.')
        elif response.status == consumer.FAILURE:
            messages.error(request, 'OpenID authentication failed.')

        if isinstance(response, consumer.FailureResponse):
            logger.error(response.message)

    return HttpResponseRedirect(reverse('chameleon_openid:openid_login'))


@anonymous_required
def openid_connect(request):
    if 'openid' not in request.session:
        return HttpResponseRedirect(reverse('chameleon_openid:openid_login'))


    openid = request.session['openid']

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            openid_identity = OpenIDUserIdentity()
            openid_identity.uid = openid['url']
            openid_identity.user = form.get_user()
            openid_identity.save()

            user = authenticate(openid_identity=openid['url'])
            if user:
                login(request, user)
                messages.success(request,
                    'You have successfully connected your OpenID account with your '
                    'Chameleon account. You are now logged in.'
                    )
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    else:
        form = AuthenticationForm(request)

    try:
        user = get_user_model().objects.filter(email=openid['sreg']['email'])
    except Exception, e:
        user = None
        logger.error(e)

    context = {
        'form': form,
        'openid': openid,
    }
    if user:
        return render(request, 'chameleon_openid/connect.html', context)
    else:
        return render(request, 'chameleon_openid/connect_or_register.html', context)


@anonymous_required
def openid_register(request):
    openid = request.session['openid']
    if request.method == 'POST':
        reg_form = UserRegistrationForm(request.POST)
        if reg_form.is_valid():
            data = reg_form.cleaned_data

            if request.POST.get('request_pi_eligibility'):
                data['piEligibility'] = 'Requested'
            else:
                data['piEligibility'] = 'Ineligible'

            data['source'] = 'Chameleon'
            logger.info('Attempting OpenID user registration: %s' % _clean_registration_data(data))
            try:
                from pytas.http import TASClient
                tas = TASClient()
                created_user = tas.save_user(None, data)

                # eager create local user and save OpenIDUserIdentity
                local_user = get_user_model().objects.create_user(
                        username=created_user['username'],
                        email=created_user['email'],
                        first_name=created_user['firstName'],
                        last_name=created_user['lastName'],
                        )

                # set not active until email confirmation
                local_user.is_active = False
                local_user.save()
                oid = OpenIDUserIdentity(uid = openid['url'], user = local_user)
                oid.save()

                messages.success(request,
                                 'Congratulations! Your account request has been ' \
                                 'received. Please check your email for account '\
                                 'verification.'
                                 )
                return HttpResponseRedirect('/')
            except Exception as e:
                logger.exception('Error saving user')
                if len(e.args) > 1:
                    if re.search('DuplicateLoginException', e.args[1]):
                        message = 'The username you chose has already been taken. ' \
                                  'Please choose another. If you already have an ' \
                                  'account with TACC, please log in using those ' \
                                  'credentials.'
                        errors = account_form._errors.setdefault('username', ErrorList())
                        errors.append(message)
                        messages.error(request, message)
                    elif re.search('DuplicateEmailException', e.args[1]):
                        forgot_password_url = reverse('tas:password_reset')
                        message = 'This email is already registered. If you already ' \
                                  'have an account with TACC, please log in using those ' \
                                  'credentials. <a href="%s">Did you forget your password?</a>' \
                                  % forgot_password_url

                        messages.error(request, message)
                        errors = profile_form._errors.setdefault('email', ErrorList())
                        errors.append(message)
                    elif re.search('PasswordInvalidException', e.args[1]):
                        message = 'The password you provided did not meet the complexity requirements.'
                        messages.error(request, message)
                        errors = account_form._errors.setdefault('password', ErrorList())
                        errors.append(message)
                    else:
                        messages.error(request,
                                       'An unexpected error occurred. If this problem '\
                                       'persists please create a help ticket.'
                                       )
                else:
                    messages.error(request,
                                   'An unexpected error occurred. If this problem ' \
                                   'persists please create a help ticket.'
                                   )
    else:
        full_name = openid['ax']['full_name'][0].split(' ')
        reg_form = UserRegistrationForm(initial={
                                                'email': openid['sreg']['email'],
                                                'firstName': full_name[0],
                                                'lastName': full_name[-1],
                                                'username': openid['sreg']['nickname']
                                            })
        try:
            username_taken = get_user_model().objects.get(username=openid['sreg']['nickname'])
            if username_taken:
                messages.warning(request,
                                 'Your GENI nickname (<b>%s</b>) is not available on ' \
                                 'Chameleon. Please choose a different username.' \
                                 % openid['sreg']['nickname']
                                 )
        except:
            pass

    context = {
        'registration_form': reg_form,
        }

    if request.method == 'POST':
        context['request_pi_eligibility'] = request.POST.get('request_pi_eligibility')

    return render(request, 'chameleon_openid/register.html', context)