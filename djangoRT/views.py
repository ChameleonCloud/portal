from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from djangoRT import rtUtil, forms, rtModels
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def mytickets(request):
    rt = rtUtil.DjangoRt()
    open_tickets = rt.getUserTickets(request.user.email, status="OPEN")
    new_tickets = rt.getUserTickets(request.user.email, status="NEW")
    response_tickets = rt.getUserTickets(request.user.email, status="RESPONSE REQUIRED")

    resolved_tickets = []
    resolved_tickets = rt.getUserTickets(request.user.email, status="RESOLVED")
    resolved_tickets.extend(rt.getUserTickets(request.user.email, status="CLOSED"))
    return render(request, 'ticketList.html', { 'open_tickets' : open_tickets, 'new_tickets' : new_tickets, 'response_tickets' : response_tickets, 'resolved_tickets' : resolved_tickets })

@login_required
def ticketdetail(request, ticketId):
    rt = rtUtil.DjangoRt()


    ticket = rt.getTicket(ticketId)
    ticket_history = rt.getTicketHistory(ticketId)
    return render(request, 'ticketDetail.html', { 'ticket' : ticket, 'ticket_history' : ticket_history, 'ticket_id' : ticketId, 'hasAccess' : rt.hasAccess(ticketId, request.user.email) })

def ticketcreate(request):
    rt = rtUtil.DjangoRt()

    data = {}
    if request.user.is_authenticated():
        data = { 'email' : request.user.email, 'first_name' : request.user.first_name, 'last_name' : request.user.last_name}
    else:
        return HttpResponseRedirect( reverse( 'djangoRT.views.ticketcreateguest'), )

    if request.method == 'POST':
        form = forms.TicketForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = rtModels.Ticket(subject = form.cleaned_data['subject'],
                    problem_description = form.cleaned_data['problem_description'],
                    requestor = form.cleaned_data['email'],
                    cc = form.cleaned_data['cc'])
            ticket_id = rt.createTicket(ticket)

            if ticket_id > -1:
                if 'attachment' in request.FILES:
                    rt.replyToTicket(ticket_id, files=(request.FILES['attachment'],))
                return HttpResponseRedirect( reverse( 'djangoRT.views.ticketdetail', args=[ ticket_id ]) )
            else:
                # make this cleaner probably
                data['subject'] = ticket.subject
                data['problem_description'] = ticket.problem_description
                data['cc'] = ticket.cc
                form = forms.TicketForm(data)
    else:
        form = forms.TicketForm(initial=data)
    return render(request, 'ticketCreate.html', { 'form' : form })

def ticketcreateguest(request):
    rt = rtUtil.DjangoRt()

    data = {}
    if request.user.is_authenticated():
        return HttpResponseRedirect( reverse( 'djangoRT.views.ticketcreate'), )

    if request.method == 'POST':
        form = forms.TicketGuestForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = rtModels.Ticket(subject = form.cleaned_data['subject'],
                    problem_description = form.cleaned_data['problem_description'],
                    requestor = form.cleaned_data['email'])
            ticket_id = rt.createTicket(ticket)

            if ticket_id > -1:
                if 'attachment' in request.FILES:
                    rt.replyToTicket(ticket_id, files=(request.FILES['attachment'],))
                messages.add_message(request, messages.SUCCESS, 'Ticket #%s has been successfully created. We will respond to your request as soon as possible.' % ticket_id)
                form = forms.TicketGuestForm()
                return render(request, 'ticketCreateGuest.html', { 'form': form })
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
    return render(request, 'ticketCreateGuest.html', { 'form' : form })

@login_required
def ticketreply(request, ticketId):
    rt = rtUtil.DjangoRt()

    ticket = rt.getTicket(ticketId)
    data = {}

    if request.method == 'POST':
        form = forms.ReplyForm(request.POST, request.FILES)

        if form.is_valid():
            if 'attachment' in request.FILES:
                if rt.replyToTicket(ticketId, text=form.cleaned_data['reply'], files=(request.FILES['attachment'],)):
                    return HttpResponseRedirect(reverse( 'djangoRT.views.ticketdetail', args=[ ticketId ] ) )
                else:
                    data['reply'] = form.cleaned_data['reply']
                    form = forms.ReplyForm(data)
            else:
                if rt.replyToTicket(ticketId, text=form.cleaned_data['reply']):
                    return HttpResponseRedirect(reverse( 'djangoRT.views.ticketdetail', args=[ ticketId ] ) )
                else:
                    data['reply'] = form.cleaned_data['reply']
                    form = forms.ReplyForm(data)

    else:
        form = forms.ReplyForm(initial=data)
    return render(request, 'ticketReply.html', { 'ticket_id' : ticketId , 'ticket' : ticket, 'form' : form, 'hasAccess' : rt.hasAccess(ticketId, request.user.email) })
