from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from djangoRT import rtUtil, forms, rtModels
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging
import mimetypes
from .models import TicketCategories
from wsgiref.util import FileWrapper

from keystoneclient import client as ks_client
from keystoneauth1.identity import v3
from keystoneauth1 import adapter, session
import json
from novaclient import client as nova_client
from blazarclient import client as blazar_client
from glanceclient import Client as glance_client
from django.conf import settings
from datetime import datetime
from dateutil import parser
import sys
from django.template.loader import render_to_string
from chameleon.keystone_auth import admin_ks_client, get_user, get_token, project_scoped_session


logger = logging.getLogger('default')

@login_required
def mytickets(request):
    rt = rtUtil.DjangoRt()
    show_resolved = 'show_resolved' in request.GET
    tickets = rt.getUserTickets(request.user.email, show_resolved=show_resolved)
    return render(request, 'djangoRT/ticketList.html', { 'tickets': tickets, 'show_resolved': show_resolved })

@login_required
def ticketdetail(request, ticketId):
    rt = rtUtil.DjangoRt()
    ticket = rt.getTicket(ticketId)
    ticket_history = rt.getTicketHistory(ticketId)

    # remove bogus "untitled" attachments
    for history in ticket_history:
        history['Attachments'] = [a for a in history['Attachments'] if not a[1].startswith('untitled (')]

    return render(request, 'djangoRT/ticketDetail.html',\
        { 'ticket' : ticket, 'ticket_history' : ticket_history, 'ticket_id' : ticketId, 'hasAccess' : rt.hasAccess(ticketId, request.user.email) })

def ticketcreate(request):
    rt = rtUtil.DjangoRt()

    if not request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'djangoRT:ticketcreateguest'), )

    data = {
        'email' : request.user.email,
        'first_name' : request.user.first_name,
        'last_name' : request.user.last_name
    }

    if request.method == 'POST':
        form = forms.TicketForm(request.POST, request.FILES)

        if form.is_valid():
            requestor_meta = '%s %s %s' % ( form.cleaned_data['first_name'], form.cleaned_data['last_name'], form.cleaned_data['email'] )
            meta = (
                ('Opened by', request.user),
                ('Category', form.cleaned_data['category']),
                ('Resource', 'Chameleon'),
            )

            header = '\n'.join('[%s] %s' % m for m in meta)
            ticket_body = '%s\n\n%s\n\n---\n%s' % ( header, form.cleaned_data['problem_description'], requestor_meta )

            region_list = []
            for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
                try:
                    token = get_token(request, region=region)
                    region_list.append(get_openstack_data(request.user.username, token, region))
                except Exception as err:
                    logger.error('error: {}'.format(err.message) + str(sys.exc_info()[0]))

            user_details = render_to_string('djangoRT/project_details.txt', {'regions': region_list})
            ticket_body = ticket_body + user_details

            ticket = rtModels.Ticket( subject = form.cleaned_data['subject'],
                                      problem_description = ticket_body,
                                      requestor = form.cleaned_data['email'],
                                      cc = form.cleaned_data['cc'] )

            logger.debug('Creating ticket for user: %s' % form.cleaned_data + ' with project details: ' + user_details)
            ticket_id = rt.createTicket(ticket)

            if ticket_id > -1:
                if 'attachment' in request.FILES:
                    rt.replyToTicket(ticket_id, files=([request.FILES['attachment'].name,\
                        request.FILES['attachment'], mimetypes.guess_type(request.FILES['attachment'].name)],))
                return HttpResponseRedirect( reverse( 'djangoRT:ticketdetail', args=[ ticket_id ]) )
            else:
                messages.error(request, 'There was an error creating your ticket. Please try again.')
        else:
            messages.error(request, 'Invalid')
    else:
        form = forms.TicketForm(initial={
            'email' : request.user.email,
            'first_name' : request.user.first_name,
            'last_name' : request.user.last_name
        })
    return render(request, 'djangoRT/ticketCreate.html', { 'form' : form })

def ticketcreateguest(request):
    rt = rtUtil.DjangoRt()

    data = {}
    if request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'djangoRT:ticketcreate'), )

    if request.method == 'POST':
        form = forms.TicketGuestForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = rtModels.Ticket(subject = form.cleaned_data['subject'],
                    problem_description = form.cleaned_data['problem_description'],
                    requestor = form.cleaned_data['email'])
            ticket_id = rt.createTicket(ticket)

            if ticket_id > -1:
                if 'attachment' in request.FILES:
                    rt.replyToTicket(ticket_id, files=([request.FILES['attachment'].name, request.FILES['attachment'], mimetypes.guess_type(request.FILES['attachment'].name)],))
                messages.add_message(request, messages.SUCCESS, 'Ticket #%s has been successfully created. We will respond to your request as soon as possible.' % ticket_id)
                form = forms.TicketGuestForm()
                return render(request, 'djangoRT/ticketCreateGuest.html', { 'form': form })
            else:
                # make this cleaner probably
                messages.error('An unexpected error occurred while creating your ticket. Please try again.')
                data['first_name'] = form.cleaned_data['first_name']
                data['last_name'] = form.cleaned_data['last_name']
                data['requestor'] = ticket.requestor
                data['subject'] = ticket.subject
                data['problem_description'] = ticket.problem_description
                data['cc'] = ticket.cc
                form = forms.TicketGuestForm(data)
    else:
        form = forms.TicketGuestForm(initial=data)
    return render(request, 'djangoRT/ticketCreateGuest.html', { 'form' : form })

@login_required
def ticketreply(request, ticketId):
    rt = rtUtil.DjangoRt()

    ticket = rt.getTicket(ticketId)
    data = {}

    if request.method == 'POST':
        form = forms.ReplyForm(request.POST, request.FILES)

        if form.is_valid():
            if 'attachment' in request.FILES:
                if rt.replyToTicket(ticketId, text=form.cleaned_data['reply'],\
                    files=([request.FILES['attachment'].name, request.FILES['attachment'], mimetypes.guess_type(request.FILES['attachment'].name)],)):
                    return HttpResponseRedirect(reverse( 'djangoRT:ticketdetail', args=[ ticketId ] ) )
                else:
                    data['reply'] = form.cleaned_data['reply']
                    form = forms.ReplyForm(data)
            else:
                if rt.replyToTicket(ticketId, text=form.cleaned_data['reply']):
                    return HttpResponseRedirect(reverse( 'djangoRT:ticketdetail', args=[ ticketId ] ) )
                else:
                    data['reply'] = form.cleaned_data['reply']
                    form = forms.ReplyForm(data)

    else:
        form = forms.ReplyForm(initial=data)
    return render(request, 'djangoRT/ticketReply.html', { 'ticket_id' : ticketId , 'ticket' : ticket, 'form' : form, 'hasAccess' : rt.hasAccess(ticketId, request.user.email) })

@login_required
def ticketclose(request, ticketId):
    rt = rtUtil.DjangoRt()

    ticket = rt.getTicket(ticketId)
    data = {}

    if request.method == 'POST':
        form = forms.CloseForm(request.POST)
        if form.is_valid():
            if rt.commentOnTicket(ticketId, text=form.cleaned_data['reply']) and rt.closeTicket(ticketId):
                return HttpResponseRedirect(reverse( 'djangoRT:ticketdetail', args=[ ticketId ] ) )
    else:
        form = forms.CloseForm(initial=data)
    return render(request, 'djangoRT/ticketClose.html', { 'ticket_id' : ticketId , 'ticket' : ticket, 'form' : form, 'hasAccess' : rt.hasAccess(ticketId, request.user.email) })


@login_required
def ticketattachment(request, ticketId, attachmentId):
    title, attachment = rtUtil.DjangoRt().getAttachment(ticketId, attachmentId)
    if attachment['Headers']['Content-Disposition'] == 'inline':
        return render(request, 'djangoRT/attachment.html', {'attachment' : attachment['Content'], 'ticketId' : ticketId, 'title' : title});
    else:
        response = HttpResponse(attachment['Content'], content_type=attachment['Headers']['Content-Type'])
        response['Content-Disposition'] = attachment['Headers']['Content-Disposition']
        return response

def get_openstack_data(username, unscoped_token, region):
    current_region = {}
    current_region['name'] = region
    current_region['projects'] = []
    ks_admin = admin_ks_client(region=region)
    ks_user = get_user(ks_admin, username)
    projects = []
    if ks_user:
        projects = ks_admin.projects.list(user=ks_user[0])
    for project in projects:
        try:
            current_project = {}
            current_project['name'] = project.name
            current_project['id'] = project.id
            current_region['projects'].append(current_project)
            psess = project_scoped_session(
                unscoped_token=unscoped_token,
                project_id=project.id,
                region=region)
            current_project['leases'] = get_lease_info(psess)
            current_project['servers'] = get_server_info(psess)
        except Exception as err:
            logger.error('error: {}'.format(err.message) + str(sys.exc_info()[0]))
    return current_region

def get_lease_info(psess):
    lease_list=[]
    blazar = blazar_client.Client('1', service_type='reservation', interface='publicURL', session=psess)
    leases = blazar.lease.list()
    for lease in leases:
        lease_dict = {}
        lease_dict['name'] = lease.get('name')
        lease_dict['status'] = lease.get('status')
        lease_dict['start_date'] = str(parser.parse(lease.get('start_date')))
        lease_dict['end_date'] = str(parser.parse(lease.get('end_date')))
        lease_dict['id'] = lease.get('id')
        lease_list.append(lease_dict)
    return lease_list

def get_server_info(psess):
    server_list=[]
    nova = nova_client.Client('2', session=psess)
    glance = glance_client('2', service_type='image', session=psess)
    servers = nova.servers.list()
    for server in servers:
        server_dict = {}
        server_dict['name'] = server.name
        server_dict['status'] = str(server.status)
        server_dict['created_date'] = str(parser.parse(server.created))
        server_dict['id'] = server.id
        image = glance.images.get(str(server.image['id']))
        server_dict['image_name'] = str(image.name)
        server_dict['image_id'] = str(image.id)
        server_list.append(server_dict)
    return server_list
