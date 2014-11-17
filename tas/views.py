from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from pytas.pytas import client as TASClient
import re
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

    if request.method == 'POST':
        data = tas.get_user( username=request.user )
        data[ 'firstName' ] = request.POST[ 'firstName' ]
        data[ 'lastName' ] = request.POST[ 'lastName' ]
        data[ 'email' ] = request.POST[ 'email' ]
        data[ 'institutionId' ] = int( request.POST[ 'institutionId' ] )
        data[ 'departmentId' ] = int( request.POST[ 'departmentId' ] )
        data[ 'countryId' ] = int( request.POST[ 'countryId' ] )
        data[ 'citizenshipId' ] = int( request.POST[ 'citizenshipId' ] )
        tas.save_user( data[ 'id' ], data )
        messages.success( request, 'Your profile has been updated!' )
        return HttpResponseRedirect( reverse( 'profile' ) )

    try:
        resp = tas.get_user( username=request.user )
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

def email_confirmation( request ):
    context = {}
    if request.method == 'POST':
        if request.POST['code'] and request.POST['username']:
            context['code'] = request.POST['code']
            context['username'] = request.POST['username']
            try:
                tas = TASClient()
                user = tas.get_user( username=context['username'] )
                tas.verify_user( user['id'], context['code'] )
                messages.success( request, 'Congratulations, your email has been verified! Please log in now.' )
                return HttpResponseRedirect( reverse( 'profile' ) )
            except Exception as e:
                if e[0] == 'User not found':
                    messages.error( request, e[1] )
                else:
                    messages.error( request, 'Email verification failed. Please check your verification code and username and try again.' )
        else:
            if request.POST['code']:
                context['code'] = request.POST['code']
            else:
                messages.error( request, 'Please enter the verification code you received via email' )

            if request.POST['username']:
                context['username'] = request.POST['username']
            else:
                messages.error( request, 'Please verify your username' )

    elif 'code' in request.GET:
        context['code'] = request.GET['code']

    return render( request, 'email_confirmation.html', context )

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
                logger.error('Error saving user', e.args)
                if len(e.args) > 1:
                    if re.search( 'DuplicateLoginException', e.args[1] ):
                        message = 'The username you chose has already been taken. Please choose another.'
                        messages.error( request, message )
                        errors['username'] = message
                    elif re.search( 'DuplicateEmailException', e.args[1] ):
                        message = 'This email is already registered.'
                        messages.error( request, message + ' <a href="{0}">Did you forget your password?</a>'.format( reverse('tas.views.password_reset') ) )
                        errors['email'] = message
                    else:
                        messages.error( request, 'An unexpected error occurred. If this problem persists please create a help ticket.' )
                else:
                    messages.error( request, 'An unexpected error occurred. If this problem persists please create a help ticket.' )
        else:
            messages.error(request, 'There was an error in your registration. See below for details.')

        context['form']['errors'] = errors
        context['form']['data'] = data
    else:
        data = {}

    try:
        inst = tas.institutions()
        context['institutions'] = inst
        if 'institutionId' in data and data['institutionId']:
            context['curr_inst'] = next((x for x in inst if x['id'] == data['institutionId']), None)
        else:
            context['curr_inst'] = None
    except Exception as e:
        logger.error( 'Error loading institutions', e )
        context['institutions'] = False

    try:
        countries = tas.countries()
        context['countries'] = countries
    except Exception as e:
        logger.error( 'Error loading countries', e )
        context['countries'] = False

    return render(request, 'register.html', context)
