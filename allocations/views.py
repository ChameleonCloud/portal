from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django import forms
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required, user_passes_test
from util.project_allocation_mapper import ProjectAllocationMapper

import logging
import json

logger = logging.getLogger(__name__)

def allocation_admin_or_superuser(user):
    if user:
        logger.debug( 'If user has allocation admin role: %s', user.groups.filter(name='Allocation Admin').count() )
        return (user.groups.filter(name='Allocation Admin').count() == 1) or user.is_superuser
    return False

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/allocations/denied/')
def index( request ):
    user = request.user
    logger.debug( 'Serving allocation approval view to: %s', user.username )
    context = {}
    return render(request, 'allocations/index.html', context)

def denied( request ):
    user = request.user
    if user:
        logger.debug( 'Denying allocation approval view to: %s', user.username )
    context = {}
    return render(request, 'allocations/denied.html', context)

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/allocations/denied/')
def view( request ):
    try:
        mapper = ProjectAllocationMapper(request)
        resp = mapper.get_all_projects()
        logger.debug( 'Total projects: %s', len(resp) )
    except Exception as e:
        logger.exception('Error loading chameleon projects')
        messages.error( request, e[0] )
        raise Exception('Error loading chameleon projects')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/allocations/denied/')
def user_select( request ):
    user = request.user
    logger.debug( 'Serving user projects view to: %s', user.username )
    context = {}
    return render(request, 'allocations/user-projects.html', context)

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/allocations/denied/')
def user_projects( request, username ):
    logger.info( 'User projects requested by admin: %s for user %s', request.user, username )
    resp = {
        'status': 'error',
        'msg': '',
        'result': []
    }
    if username:
        try:
            mapper = ProjectAllocationMapper(request)
            user_projects = mapper.get_user_projects(username)
            resp['status'] = 'success'
            resp['result'] = user_projects
            logger.info('Total chameleon projects for user %s: %s', username, len(user_projects))
        except Exception as e:
            logger.debug('Error loading projects for user: %s with error %s', username, e)
            resp['msg'] = 'Error loading projects for user: %s' %username
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/allocations/denied/')
def approval( request ):
    resp = {}
    errors = {}
    status = ''
    if request.POST:
        mapper = ProjectAllocationMapper(request)
        data = json.loads(request.body)
        data['reviewer'] = request.user.username
        data['reviewerId'] = mapper.get_user_id(request)
        logger.info( 'Allocation approval requested by admin: %s', request.user )
        logger.info( 'Allocation approval request data: %s', json.dumps( data ) )
        validate_datestring = validators.RegexValidator( '^\d{4}-\d{2}-\d{2}$' )
        validate_datetimestring = validators.RegexValidator( '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$' )
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
                    errors['start'] = 'Start date must be a valid date string e.g. "2015-05-20" .'
            elif data['status'].lower() == 'approved':
                errors['start'] = 'Start date is required.'

            if data['end']:
                try:
                    validate_datestring( data['end'] )
                except ValidationError:
                    errors['end'] = 'Start date must be a valid date string e.g. "2015-05-20" .'
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
                validate_datetimestring(data['dateRequested'])
            except ValidationError:
                errors['dateRequested'] = 'Requested date must be a valid date string e.g. "2015-05-20T05:00:00Z" .'
        #else:
        #     errors['dateRequested'] = 'Requested date is required.'

        if data['dateReviewed']:
            try:
                validate_datestring( data['dateReviewed'] )
            except ValidationError:
                errors['dateReviewed'] = 'Reviewed date must be a valid date string e.g. "2015-05-20" .'
        else:
            errors['dateReviewed'] = 'Reviewed date is required.'
        if len( errors ) == 0:
            # source
            data['source'] = 'Chameleon'

            try:
                mapper.allocation_approval(data, request.get_host())
                status = 'success'
            except Exception as e:
                logger.exception('Error processing allocation approval.')
                status = 'error'
                errors['message'] = 'An unexpected error occurred. If this problem persists please create a help ticket.'

        else:
            logger.info( 'Request data failed validation. %s', list(errors.values()))
            status = 'error'

    else:
        status = 'error'
        errors['message'] = 'Only POST method allowed.'
    resp['status'] = status
    resp['errors'] = errors
    return HttpResponse(json.dumps(resp), content_type="application/json")

def allocations_template(request, resource):
    logger.debug('Template requested: %s.html', resource)
    templateUrl = 'allocations/%s.html' %resource
    return render_to_response(templateUrl)
