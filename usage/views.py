from datetime import datetime, timedelta, date

from pytz import timezone
from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django import forms
from pytas.http import TASClient, JobsClient
from tas.forms import PasswordResetRequestForm, PasswordResetConfirmForm
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.serializers.json import DjangoJSONEncoder
from .models import Downtime
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
        jobsClient = JobsClient()
        start_date = request.GET.get('from')
        end_date = request.GET.get('to')
        logger.debug("Getting some jobs for chameleon, start=" + start_date + ", end=" + end_date)
        if allocation_id is not None:
            logger.debug("allocation=" + allocation_id)
        if username is not None:
            logger.debug("username=" + username)
        if queue is not None:
            logger.debug("queue=" + queue)
        jobs = jobsClient.get_jobs('chameleon', start_date, end_date, allocation_id, username, queue)
        logger.debug("Done fetching jobs")
        logger.info( 'Total jobs: %s', len( jobs ) )
        data = []
        for job in jobs:
            logger.info('endDate: %s', job.get('endDate'))
            endDate = calendar.timegm(time.strptime( job.get('endDate'), "%Y-%m-%dT%H:%M:%S" )) * 1000
            sus = job.get('suCharge')
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
        #tas = TASClient()
        tas = JobsClient()
        logger.debug(
            "Getting some jobs for chameleon, start=" + start_date + ", end=" + end_date + ", allocation=" + allocation_id)
        jobs = tas.get_jobs('chameleon', start_date, end_date, allocation_id)
        logger.debug("Done fetching jobs")
        logger.info( 'Total jobs: %s', len( jobs ) )
        for job in jobs:
            username = job.get('userLogin')
            queueName = job.get('queueName')
            if username not in resp:
                resp[username] = {}
            if queueName not in resp[username]:
                resp[username][queueName] = job.get('suCharge')
            else:
                resp[username][queueName] += job.get('suCharge')
    except Exception as e:
        traceback.print_exc()
        raise Exception('Error fetching jobs.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_downtimes_json( request):
    start_date = request.GET.get('from')
    logger.info('start_date: %s', start_date)
    end_date = request.GET.get('to')
    logger.info('end_date: %s', end_date)
    queue = request.GET.get('queue')
    central = timezone('US/Central')
    logger.info( 'Downtimes requested from: %s, to: %s for queue: %s', start_date, end_date, queue)
    resp = {}
    try:
        if start_date is None:
            start_date = central.localize(datetime(2014, 1, 1, 0, 0, 0))
            logger.info('start_date: %s', start_date)
        else:
            arr = start_date.split('-')
            start_date = central.localize(datetime(int(arr[0]), int(arr[1]), int(arr[2]), 0, 0, 0))

        if end_date is None:
            end_date = central.localize(datetime.now()) + timedelta(days=365)
            logger.info('end_date: %s', end_date)
        else:
            arr = end_date.split('-')
            end_date = central.localize(datetime(int(arr[0]), int(arr[1]), int(arr[2]), 23, 59, 59))

        
        args = (Q(start__lte = start_date) & Q(end__gte = start_date))|(Q(start__lte = end_date) & Q(end__gte = end_date))|(Q(start__gte = start_date) & Q(end__lte = end_date))
        if queue is not None:
            logger.info( 'Querying downtimes from: %s, to: %s for queue: %s', start_date, end_date, queue)
            downtimes = Downtime.objects.filter(args, queue__iexact=queue).order_by('start')
        else:
            logger.info( 'Querying downtimes from: %s, to: %s', start_date, end_date)
            downtimes = Downtime.objects.filter(args).order_by('start')
        
        temp = {}
        for downtime in downtimes:
            nodes_down = -1;
            downtime_start = downtime.start.astimezone(central)
            downtime_end = downtime.end.astimezone(central)
            if downtime_start > start_date:
                chunked_start = downtime_start
            else:
                chunked_start = start_date

            if downtime_end > end_date:
                downtime_end = end_date

            #interval = downtime.end - chunked_start
            interval = downtime_end - chunked_start
            repeat = True
            while (repeat):
                date_string = chunked_start.strftime('%Y-%m-%d')
                if interval.days > 0:
                    chunked_end = central.localize(datetime(chunked_start.year, chunked_start.month, chunked_start.day, 23, 59, 59))
                    chunked_interval = chunked_end - chunked_start
                    diff_in_hours = round(chunked_interval.total_seconds()/3600, 2)
                    nodes_down = round((downtime.nodes_down * diff_in_hours)/24, 2)
                    chunked_start = central.localize(datetime(chunked_start.year, chunked_start.month, chunked_start.day, 0, 0, 0)) + timedelta(days=1)
                    interval = downtime_end - chunked_start
                else:
                    diff_in_hours = round(interval.total_seconds()/3600, 2)
                    nodes_down = round((downtime.nodes_down * diff_in_hours)/24, 2)
                    repeat = False

                key = date_string
                if key in temp:
                    temp[key]['nodes_down'] += nodes_down
                else:
                    if nodes_down > 0:
                        temp[key] = {}
                        temp[key]['nodes_down'] = nodes_down
                        temp[key]['date'] = date_string
        resp['result'] = temp.values()
        resp['status'] = 'success'
        resp['message'] = ''
    except Exception as e:
        traceback.print_exc()
        raise Exception('Error fetching downtimes.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def get_daily_usage_json( request):
    start_date_str = request.GET.get('from')
    end_date_str = request.GET.get('to')
    resp = {}
    resp['result'] = None
    resp['status'] = 'error'
    if start_date_str is None or end_date_str is None:
        resp['message'] = 'Start and end date are required.'

    queue = request.GET.get('queue')
    resource = 'chameleon'
    logger.info( 'Daily usage requested from: %s, to: %s for queue: %s', start_date_str, end_date_str, queue)
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    if start_date > end_date:
        resp['message'] = 'Start date must be before end date.'
    temp = {}
    while(end_date >= start_date):
        str_start_date = start_date.strftime('%Y-%m-%d')
        temp[str_start_date] = {}
        temp[str_start_date]['date'] = str_start_date
        temp[str_start_date]['nodes_used'] = 0
        start_date += timedelta(days=1)
    try:
        #tas = TASClient()
        tas = JobsClient()
        allocation_id = 27591
        # use start, end date and queue here to get jobs
        jobs = tas.get_jobs(resource, start_date_str, end_date_str, allocation_id)
        logger.info( 'Total jobs: %s', len( jobs ) )
        data = []
        for job in jobs:
            job_start_date_str = job.get('start')
            job_end_date_str = job.get('end')
            job_start_date = datetime.strptime(job_start_date_str, '%Y-%m-%dT%H:%M:%S')
            job_end_date = datetime.strptime(job_end_date_str, '%Y-%m-%dT%H:%M:%S')
            interval = job_end_date - job_start_date
            logger.info('Job start date: %s, end date: %s, interval %s', job_start_date, job_end_date, interval)
            diff_in_hours = round(interval.total_seconds()/3600, 2)
            sus = job.get('suCharge')
            nodes_used = round((sus * diff_in_hours)/24, 2)
            logger.info('Diff in hours: %s, sus: %s, Nodes used: %s', diff_in_hours, sus, nodes_used)
            if job_end_date_str:
                time_index = job_end_date_str.index('T')
                job_end_date_str = job_end_date_str[:time_index]
                if job_end_date_str in temp:
                    temp[job_end_date_str]['nodes'] += nodes_used

        resp['result'] = temp.values()
        resp['status'] = 'success'
        resp['message'] = ''
    except Exception as e:
        traceback.print_exc()
        raise Exception('Error fetching jobs.')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@user_passes_test(allocation_admin_or_superuser, login_url='/admin/usage/denied/')
def utilization( request):
    logger.info( 'Utilization page requested.')
    context = {}
    return render(request, 'usage/utilization.html', context)


def usage_template(request, resource):
    logger.debug('Template requested: %s.html', resource)
    templateUrl = 'allocations/%s.html' %resource
    return render_to_response(templateUrl)
