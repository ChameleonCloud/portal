from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from pytas.pytas import client as TASClient
import logging
import json

logger = logging.getLogger('tas')

@login_required
def profile( request ):
    context = {}

    try:
        tas = TASClient()
        resp = tas.get_user(username=request.user)
        context['profile'] = resp
    except:
        context['profile'] = False
        # raise Exception('error loading profile')

    if context['profile']['source'] != 'Chameleon':
        messages.info( request, 'Your account was created outside of the Chameleon Portal. Please visit the <a target="_blank" href="https://portal.tacc.utexas.edu">TACC User Portal</a> to edit your profile.' )

    return render(request, 'profile.html', context)

@login_required
def profile_edit( request ):
    context = {}

    tas = TASClient()
    try:
        resp = tas.get_user(username=request.user)
        context['profile'] = resp
    except:
        context['profile'] = False
        # raise Exception('error loading profile')

    if context['profile']['source'] != 'Chameleon':
        return HttpResponseRedirect( reverse( 'profile' ) )

    try:
        inst = tas.institutions()
        context['institutions'] = inst

        curr_inst = next( ( x for x in inst if x['id'] == context['profile']['institutionId'] ), None)
        context['curr_inst'] = curr_inst
    except Exception as e:
        print e
        context['institutions'] = False


    try:
        countries = tas.countries()
        context['countries'] = countries
    except:
        context['countries'] = False

    return render(request, 'profile_edit.html', context)

# TODO!
def password_reset( request ):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'profile' ) )

    if request.POST:
        uname = request.POST['username']
        print uname
        if uname:
            messages.success(request, 'Your request has been received. If an account matching the username you provided is found, you will receive an email with further instructions to complete the password reset process.')
            return redirect( 'django.contrib.auth.views.login' )
        else:
            messages.error(request, 'Please provide your Chameleon Cloud Username')

    return render(request, 'password_reset.html')

def register( request ):
    if request.user is not None and request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'profile' ) )

    tas = TASClient()

    context = { 'form': {} }
    if request.POST:
        data = request.POST.copy()
        errors = {}

        if not data['firstName']:
            errors['firstName'] = 'Please provide your first name'

        if not data['lastName']:
            errors['lastName'] = 'Please provide your last name'

        if data['username']:
            validate_username = validators.RegexValidator( '[a-z][a-z0-9_]{2,7}', 'Please enter a valid username.' )
            try:
                validate_username( data['username'] )
            except ValidationError as e:
                errors['username'] = e[0]
        else:
            errors['username'] = 'Please select a username'

        if data['email']:
            try:
                validators.validate_email( data['email'] )
            except ValidationError as e:
                errors['email'] = e[0]
        else:
            errors['email'] = 'Please provide a valid email address'

        if data['institutionId']:
            data['institutionId'] = int( data['institutionId'] )
        else:
            errors['institutionId'] = 'Please select your affilitated Institution'

        if data['departmentId']:
            data['departmentId'] = int( data['departmentId'] )

        if data['countryId']:
            data['countryId'] = int( data['countryId'] )
        else:
            errors['countryId'] = 'Please provide your current country of residence'

        if data['citizenshipId']:
            data['citizenshipId'] = int( data['citizenshipId'] )
        else:
            errors['citizenshipId'] = 'Please provide your country of citizenship'

        if data['password'] and data['confirm_password']:
            if data['password'] != data['confirm_password']:
                errors['password'] = 'The passwords provided do not match'
        else:
            errors['password'] = 'Please provide and confirm your password'


        if len( errors ) == 0:
            # success!

            # source
            data['source'] = 'Chameleon'

            # TODO?
            # pi eligible
            data['piEligibility'] = 'Ineligible'

            # log the request
            logger.info('processing user registration: ' + str(data))

            try:
                created_user = tas.save_user( None, data )
                print created_user

                messages.success(request, 'Congratulations! Your account request has been received. Please check your email for account verification.')
                return HttpResponseRedirect( '/' )
            except Exception as e:
                logger.error('Error saving user')
                logger.error(e.args)
                messages.error(request, 'An unexpected error occurred. If this problem persists please create a help ticket.')
        else:
            messages.error(request, 'There was an error in your registration. See below for details.')

        context['form']['errors'] = errors
        context['form']['data'] = data
    else:
        data = {}

    try:
        inst = tas.institutions()
        context['institutions'] = inst

        # todo
        if 'institutionId' in data and data['institutionId']:
            context['curr_inst'] = next((x for x in inst if x['id'] == data['institutionId']), None)
        else:
            context['curr_inst'] = None
    except Exception as e:
        print e
        context['institutions'] = False

    try:
        countries = tas.countries()
        context['countries'] = countries
    except:
        context['countries'] = False

    return render(request, 'register.html', context)
