from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django import forms
from pytas.pytas import client as TASClient
from tas.forms import PasswordResetRequestForm, PasswordResetConfirmForm
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required, user_passes_test

import re
import logging
import json
import math
import time

logger = logging.getLogger('default')

def not_allocation_admin_or_superuser(user):
    logger.debug( 'user=%s', user )
    if user:
        logger.debug( 'user groups count=%s', user.groups.filter(name='Allocation Admin').count() )
        return (user.groups.filter(name='Allocation Admin').count() == 1) or user.is_superuser
    return False

@login_required
@user_passes_test(not_allocation_admin_or_superuser, login_url='/allocations/denied/')
def index( request ):
    user = request.user
    if user:
        logger.debug( 'group=%s', user.groups )
    context = {}
    return render(request, 'allocations/index.html', context)

def denied( request ):
    context = {}
    return render(request, 'allocations/denied.html', context)

@login_required
@user_passes_test(not_allocation_admin_or_superuser, login_url='/allocations/denied/')
def view( request ):
    resp = ''
    try:
        tas = TASClient()
        resp = tas.projects()
    except Exception as e:
        logger.exception('error loading projects')
        messages.error( request, e[0] )
        raise Exception('error loading projects')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(not_allocation_admin_or_superuser, login_url='/allocations/denied/')
def view_test( request ):
    resp = {}
    try:
        fd = open('allocations/fixtures/projects.json', 'r')
        resp = json.loads(fd.read())
        fd.close()
    except:
        print 'Could not load allocations/fixtures/projects.json'
    return HttpResponse(json.dumps(resp['result']), content_type="application/json")

@login_required
@user_passes_test(not_allocation_admin_or_superuser, login_url='/allocations/denied/')
def approval( request ):
    resp = {}
    errors = {}
    status = ''
    if request.POST:
        tas = TASClient()
        userData = tas.get_user( username=request.user )
        data = json.loads(request.body)
        data['reviewer'] = userData['username']
        data['reviewerId'] = userData['id']
        validate_datestring = validators.RegexValidator( '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$' )
        if not data['decisionSummary']:
            errors['decisionSummary'] = 'Decision Summary is required.'

        if not data['status']:
            errors['status'] = 'Status is required. '
        elif not data['status'] in ['Pending', 'pending', 'Approved', 'approved', 'Rejected', 'rejected']:
            errors['status'] = 'Status must be "Pending", "pending", "Approved", "approved", "Rejected", "rejected"'
        else:
            if data['start']:
                try:
                    validate_datestring( data['start'] )
                except ValidationError:
                    errors['start'] = 'Start date must be a valid date string e.g. "2015-05-20T05:00:00Z" .'
            elif data['status'].lower() == 'approved':
                 errors['start'] = 'Start date is required.'

            if data['end']:
                try:
                    validate_datestring( data['end'] )
                except ValidationError:
                    errors['end'] = 'Start date must be a valid date string e.g. "2015-05-20T05:00:00Z" .'
            elif data['status'].lower() == 'approved':
                 errors['end'] = 'Start date is required.'

        if data['computeAllocated']:
            try:
                data['computeAllocated'] = int( data['computeAllocated'] )
            except ValueError:
                errors['computeAllocated'] = 'Compute Allocated must be a number.'

        if data['computeRequested']:
            try:
                data['computeRequested'] = int( data['computeRequested'] )
            except ValueError:
                errors['computeRequested'] = 'Compute Requested must be a number.'

        if data['storageAllocated']:
            try:
                data['storageAllocated'] = int( data['storageAllocated'] )
            except ValueError:
                errors['storageAllocated'] = 'Storage Allocated must be a number.'

        if data['storageRequested']:
            try:
                data['storageRequested'] = int( data['storageRequested'] )
            except ValueError:
                errors['storageRequested'] = 'Storage Requested must be a number.'

        if data['memoryAllocated']:
            try:
                data['memoryAllocated'] = int( data['memoryAllocated'] )
            except ValueError:
                errors['memoryAllocated'] = 'Memory Allocated must be a number.'

        if data['memoryRequested']:
            try:
                data['memoryRequested'] = int( data['memoryRequested'] )
            except ValueError:
                errors['memoryRequested'] = 'Memory Requested must be a number.'

        if data['projectId']:
            try:
                data['projectId'] = int( data['projectId'] )
            except ValueError:
                errors['projectId'] = 'Project id must be number.'
        else:
            errors['projectId'] = 'Project id is required.'

        if not data['project']:
            errors['project'] = 'Project charge code is required.'

        if data['reviewerId']:
            try:
                data['reviewerId'] = int( data['reviewerId'] )
            except ValueError:
                errors['reviewerId'] = 'Reviewer id must be number.'
        else:
            errors['reviewerId'] = 'Reviewer id is required.'

        if not data['reviewer']:
            errors['reviewer'] = 'Reviewer username is required.'

        if data['dateRequested']:
            try:
                validate_datestring( data['dateRequested'] )
            except ValidationError:
                errors['dateRequested'] = 'Requested date must be a valid date string e.g. "2015-05-20T05:00:00Z" .'
        #else:
        #     errors['dateRequested'] = 'Requested date is required.'

        if data['dateReviewed']:
            try:
                validate_datestring( data['dateReviewed'] )
            except ValidationError:
                errors['dateReviewed'] = 'Reviewed date must be a valid date string e.g. "2015-05-20T05:00:00Z" .'
        else:
             errors['dateReviewed'] = 'Reviewed date is required.'
        if len( errors ) == 0:
            # source
            data['source'] = 'Chameleon'

            # log the request
            logger.info( 'processing allocation approval: data=%s', json.dumps( data ) )

            try:
                decided_allocation = tas.allocation_approval( data['id'], data )
                logger.info('allocation approval TAS response: data=%s', json.dumps(decided_allocation))
                # success!
                #time.sleep(5)
                status = 'success'
            except Exception as e:
                logger.exception('Error processing allocation approval, data=%s', json.dumps( data ))
                status = 'error'
                errors['message'] = 'An unexpected error occurred. If this problem persists please create a help ticket.'

        else:
            status = 'error'

    else:
        status = 'error'
        errors['message'] = 'Only POST method allowed.'
    resp['status'] = status
    resp['errors'] = errors
    return HttpResponse(json.dumps(resp), content_type="application/json")

def allocations_template(request, resource):
    templateUrl = 'allocations/%s.html' %resource
    return render_to_response(templateUrl)
