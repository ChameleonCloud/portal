from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.forms.util import ErrorList
from django.http import HttpResponse, HttpResponseRedirect
from django import forms
from django.contrib.auth.models import User
from pytas.http import TASClient
from tas.forms import EmailConfirmationForm, PasswordResetRequestForm, \
                      PasswordResetConfirmForm, UserProfileForm, UserRegistrationForm, RecoverUsernameForm
from tas.models import activate_local_user
from djangoRT import rtUtil, rtModels
import re
import logging
import json

logger = logging.getLogger(__name__)

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

    if context['profile']['source'] != 'Chameleon':
        messages.info(request,
                      'Your account was created outside of the Chameleon Portal. ' \
                      'Please visit the <a target="_blank" href="https://portal.tacc.utexas.edu">'\
                      'TACC User Portal</a> to edit your profile.')

    return render(request, 'tas/profile.html', context)

def get_departments_json(request):
    institutionId = request.GET.get('institutionId')
    if institutionId:
        tas = TASClient()
        departments = tas.get_departments(institutionId)
    else:
        departments = {}
    return HttpResponse(json.dumps(departments), content_type='application/json')

def _create_ticket_for_pi_request(user):
    """
    This is a stop-gap solution for https://collab.tacc.utexas.edu/issues/8327.
    """
    rt = rtUtil.DjangoRt()
    subject = "Chameleon PI Eligibility Request: %s" % user['username']
    ticket = rtModels.Ticket(subject = subject,
                             problem_description = "",
                             requestor = "us@tacc.utexas.edu")
    rt.createTicket(ticket)

@login_required
def profile_edit(request):
    tas = TASClient()
    tas_user = tas.get_user(username=request.user)

    if tas_user['source'] != 'Chameleon':
        return HttpResponseRedirect(reverse('tas:profile'))

    if request.method == 'POST':
        form = UserProfileForm(request.POST, initial=tas_user)
        if form.is_valid():
            data = form.cleaned_data
            if request.POST.get('request_pi_eligibility'):
                data['piEligibility'] = 'Requested'
                _create_ticket_for_pi_request(tas_user)
            else:
                data['piEligibility'] = tas_user['piEligibility']
            data['source'] = 'Chameleon'
            tas.save_user(tas_user['id'], data)
            messages.success(request, 'Your profile has been updated!')
            return HttpResponseRedirect(reverse('tas:profile'))
    else:
        form = UserProfileForm(initial=tas_user)

    context = {
        'form': form,
        'user': tas_user,
        }
    return render(request, 'tas/profile_edit.html', context)

def recover_username(request):

    if request.POST:
        form = RecoverUsernameForm(request.POST)
        if form.is_valid():
            email = request.POST['email']
            try:
                user = User.objects.get(email=email)
                send_mail(
                    'Your Chameleon Username',
                    'Your Chameleon username is ' + user.username,
                    'no-reply@chameleoncloud.org',
                    [email],
                    fail_silently=False,
                )

                messages.success(request, 'Your username has been sent to the email you provided.')
            except ObjectDoesNotExist:
                messages.success(request, 'Your username has been sent to the email you provided.')
    else:
        form = RecoverUsernameForm()
    return render(request, 'tas/recover_username.html', { 'form': form })

def password_reset(request):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect(reverse('tas:profile'))

    if request.POST:
        if 'code' in request.GET:
            form = PasswordResetConfirmForm(request.POST)
            if _process_password_reset_confirm(request, form):
                messages.success(request, 'Your password has been reset! You can now log in using your new password')
                return HttpResponseRedirect(reverse('tas:profile'))
        else:
            form = PasswordResetRequestForm(request.POST)
            if _process_password_reset_request(request, form):
                form = PasswordResetRequestForm()

    elif 'code' in request.GET:
        form = PasswordResetConfirmForm(initial={ 'code': request.GET['code'] })
        form.fields['code'].widget = forms.HiddenInput()
    else:
        form = PasswordResetRequestForm()

    if 'code' in request.GET:
        message = 'Confirm your password reset using the form below. Enter your Chameleon username and new password to complete the password reset process.'
    else:
        message = 'Enter your Chameleon username to request a password reset. If your account is found, you will receive an email at the registered email address with instructions to complete the password reset.'

    return render(request, 'tas/password_reset.html', { 'message': message, 'form': form })

def _process_password_reset_request(request, form):
    if form.is_valid():
        # always show success to prevent data leaks
        messages.success(request, 'Your request has been received. If an account matching the username you provided is found, you will receive an email with further instructions to complete the password reset process.')

        username = form.cleaned_data['username']
        logger.info('Password reset request for username: "%s"', username)
        try:
            tas = TASClient()
            user = tas.get_user(username=username)
            resp = tas.request_password_reset(user['username'], source='Chameleon')
            logger.debug(resp)
        except:
            logger.exception('Failed password reset request')

        return True
    else:
        return False

def _process_password_reset_confirm(request, form):
    if form.is_valid():
        data = form.cleaned_data
        try:
            tas = TASClient()
            return tas.confirm_password_reset(data['username'], data['code'], data['password'], source='Chameleon')
        except Exception as e:
            logger.exception('Password reset failed')
            if len(e.args) > 1:
                if re.search('account does not match', e.args[1]):
                    form.add_error('username', e.args[1])
                elif re.search('No password reset request matches', e.args[1]):
                    form.add_error('code', e.args[1])
                elif re.search('complexity requirements', e.args[1]):
                    form.add_error('password', e.args[1])
                elif re.search('expired', e.args[1]):
                    form.add_error('code', e.args[1])
                else:
                    form.add_error('__all__', 'An unexpected error occurred. Please try again')
            else:
                form.add_error('__all__', 'An unexpected error occurred. Please try again')

    return False

def email_confirmation(request):
    context = {}
    if request.method == 'POST':
        form = EmailConfirmationForm(request.POST)
        if form.is_valid():
            code = request.POST['code']
            username = request.POST['username']
            #send_opt_in_email(username)
            try:
                tas = TASClient()
                user = tas.get_user(username=username)
                tas.verify_user(user['id'], code)
                activate_local_user(username)
                messages.success(request, 'Congratulations, your email has been verified! Please log in now.')
                send_opt_in_email(username)
                return HttpResponseRedirect(reverse('tas:profile'))
            except Exception as e:
                logger.exception('Email verification failed')
                if e[0] == 'User not found':
                    form.add_error('username', e[1])
                else:
                    form.add_error('code', 'Email verification failed. Please check your verification code and username and try again.')

    else:
        form = EmailConfirmationForm(initial={'code': request.GET.get('code', '')})

    context['form'] = form

    return render(request, 'tas/email_confirmation.html', context)

def send_opt_in_email(username):
    try:
        template = 'tas/email_subscription_opt_in.html'
        user = User.objects.get(username=username)
        email_message = render_to_string(template, {'user': user})
        logger.info(email_message)
        send_mail(subject='Welcome to Chameleon',message=None,from_email='no-reply@chameleoncloud.org',recipient_list=[user.email],fail_silently=False,html_message=email_message)
    except Exception as e:
        logger.error(e)
        return


def register(request):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect(reverse('tas:profile'))

    if request.method == 'POST':
        register_form = UserRegistrationForm(request.POST)
        if register_form.is_valid():
            data = register_form.cleaned_data

            if request.POST.get('request_pi_eligibility'):
                data['piEligibility'] = 'Requested'
            else:
                data['piEligibility'] = 'Ineligible'

            data['source'] = 'Chameleon'
            logger.info('Attempting new user registration: %s' % _clean_registration_data(data))
            try:
                tas = TASClient()
                created_user = tas.save_user(None, data)

                if data['piEligibility'] == 'Requested':
                    _create_ticket_for_pi_request(created_user)

                messages.success(request, 'Congratulations! Your account request has been received. Please check your email for account verification.')
                return HttpResponseRedirect('/')
            except Exception as e:
                logger.exception('Error saving user')
                if len(e.args) > 1:
                    if re.search('DuplicateLoginException', e.args[1]):
                        message = 'The username you chose has already been taken. Please choose another. If you already have an account with TACC, please log in using those credentials.'
                        errors = register_form._errors.setdefault('username', ErrorList())
                        errors.append(message)
                        messages.error(request, message)
                    elif re.search('DuplicateEmailException', e.args[1]):
                        message = 'This email is already registered. If you already have an account with TACC, please log in using those credentials.'
                        messages.error(request, message + ' <a href="{0}">Did you forget your password?</a>'.format(reverse('tas:password_reset')))
                        errors = register_form._errors.setdefault('email', ErrorList())
                        errors.append(message)
                    elif re.search('PasswordInvalidException', e.args[1]):
                        message = 'The password you provided did not meet the complexity requirements.'
                        messages.error(request, message)
                        errors = register_form._errors.setdefault('password', ErrorList())
                        errors.append(message)
                    else:
                        messages.error(request, 'An unexpected error occurred. If this problem persists please create a help ticket.')
                else:
                    messages.error(request, 'An unexpected error occurred. If this problem persists please create a help ticket.')

            # return HttpResponseRedirect(reverse('tas:profile'))
    else:
        register_form = UserRegistrationForm()

    context = {
        'register_form': register_form,
        }

    if request.method == 'POST':
        context['request_pi_eligibility'] = request.POST.get('request_pi_eligibility')

    return render(request, 'tas/register.html', context)

def _clean_registration_data(registration_data):
    hide_keys = ['password', 'confirm_password', 'confirmPassword']
    return dict((k, v) for k, v in registration_data.iteritems() if k not in hide_keys)
