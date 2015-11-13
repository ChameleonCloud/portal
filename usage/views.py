from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django import forms
from pytas.http import TASClient
from tas.forms import PasswordResetRequestForm, PasswordResetConfirmForm
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required, user_passes_test

import re
import logging
import traceback
import json
import math
import time
import calendar

logger = logging.getLogger('default')

def allocation_admin_or_superuser(user):
    if user:
        logger.debug( 'If user has allocation admin role: %s', user.groups.filter(name='Allocation Admin').count() )
        return (user.groups.filter(name='Allocation Admin').count() == 1) or user.is_superuser
    return False

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def project_usage( request ):
    user = request.user
    logger.debug( 'Serving admin usage view to: %s', user.username )
    context = {}
    return render(request, 'usage/project-usage.html', context)

def denied( request ):
    user = request.user
    if user:
        logger.debug( 'Denying admin usage view to: %s', user.username )
    context = {}
    return render(request, 'usage/permission-denied.html', context)

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def user_select( request ):
    user = request.user
    logger.debug( 'Serving user projects view to: %s', user.username )
    context = {}
    return render(request, 'usage/user-usage.html', context)

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_projects_json( request, username=None ):
    logger.info( 'Projects requested.')
    resp = []
    try:
        tas = TASClient()
        chameleonProjects = tas.projects_for_group('Chameleon')
        if username is not None:
            userProjects = tas.projects_for_user( username=username )
            if (chameleonProjects and userProjects):
                for project in userProjects:
                    if project in chameleonProjects:
                        resp.append(project)
                        logger.info( 'Total chameleon projects for user %s: %s', username, len( resp ) )
        else:
            logger.info( 'Total chameleon projects: %s', username, len( chameleonProjects ) )
            resp = chameleonProjects

    except Exception as e:
        traceback.print_exc()
        raise Exception('Error loading projects.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_project_users_json( request, project_id=None ):
    logger.info( 'Projects users requested.')
    resp = []
    try:
        tas = TASClient()
        if project_id is not None:
            resp = tas.get_project_users( project_id=project_id )
            logger.info( 'Total users for project %s: %s', project_id, len( resp ) )
        else:
            raise Exception('Project id is required.')

    except Exception as e:
        traceback.print_exc()
        raise Exception('Error loading projects users.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_allocation_usage_json( request, allocation_id=None, username=None, queue=None, **kwargs ):
    logger.info( 'Allocations requested.')
    data = []
    try:
        tas = TASClient()
        jobs = tas.get_jobs(allocation_id, username, queue)
        logger.info( 'Total jobs: %s', len( jobs ) )
        data = []
        for job in jobs:
            logger.info('endUTC: %s', job.get('endUTC'))
            endDate = calendar.timegm(time.strptime( job.get('endUTC'), "%Y-%m-%dT%H:%M:%S" )) * 1000
            sus = job.get('sus')
            item = [endDate, sus]
            data.append(item)
    except Exception as e:
        traceback.print_exc()
        raise Exception('Error fetching jobs.')
    return HttpResponse(json.dumps(data), content_type="application/json")

@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_usage_by_users_json( request, allocation_id=None):
    start_date = request.GET.get('from')
    end_date = request.GET.get('to')
    if not re.match(r'^\d{4}-\d{2}-\d{2}', start_date) or not re.match(r'^\d{4}-\d{2}-\d{2}', end_date):
        raise Exception('Start date and end date params must be in the format: YYYY-MM-dd')
    logger.info( 'Usage by users requested for allocation id: %s, from: %s, to: %s', allocation_id, start_date, end_date)
    resp = {}
    try:
        tas = TASClient()
        jobs = tas.get_jobs(allocation_id)
        logger.info( 'Total jobs: %s', len( jobs ) )
        for job in jobs:
            username = job.get('username')
            queueName = job.get('queueName')
            if username not in resp:
                resp[username] = {}
            if queueName not in resp[username]:
                resp[username][queueName] = job.get('sus')
            else:
                resp[username][queueName] += job.get('sus')
    except Exception as e:
        traceback.print_exc()
        raise Exception('Error fetching jobs.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

def usage_template(request, resource):
    logger.debug('Template requested: %s.html', resource)
    templateUrl = 'allocations/%s.html' %resource
    return render_to_response(templateUrl)
