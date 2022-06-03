from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from djangoRT import rtUtil, forms, rtModels
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
import logging
import mimetypes
from datetime import datetime

from novaclient import client as nova_client
from blazarclient import client as blazar_client
from glanceclient import Client as glance_client
from ironicclient import client as ironic_client
from dateutil import parser
from chameleon.keystone_auth import admin_session, admin_ks_client
from projects.models import Project
from util.keycloak_client import KeycloakClient
from .tasks import add_openstack_data

logger = logging.getLogger("default")


QUESTION_GROUPS = [
    {
        "label": "Reservations",
        "desc": "When submitting a ticket regarding reservations, please include the lease ID if possible.",
        "questions": [
            {
                "label": "Lease is missing resources",
                "desc": """If your lease is missing resources, then one of its nodes was
            detected as unhealthy. There was no replacement that could be
            found at the time. If you check the
            <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
            for the site you are using, you may be able to create a second
            lease to make up for the missing resources.""",
            },
            {
                "label": "A node isn't working in my lease",
                "desc": """If a node in your lease is causing issues, you can try to create
            a second lease to make up the troublesome one. Please submit a
            ticket including the problematic lease ID, and if known, the
            ID of the node so that we can investigate the node.""",
            },
            {
                "label": "Creating a lease fails",
                "desc": """If your lease fails with a message saying "Not enough resources..."
                then either the resources matching your query are reserved (see the
                <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
                to check) or your query doesn't match any resources, in which case
                double check that the resource type or ID you specify is correct.""",
            },
            {
                "label": "I can't renew my lease",
                "desc": """Renewing a lease requires that it's resources are not reserved
                by others during the period you are renewing for. See the
                <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
                to make sure your reserved resources are free. If they are not,
                you can create a
                <a href="https://chameleoncloud.readthedocs.io/en/latest/technical/images.html#the-cc-snapshot-utility">snapshot</a>
                of your image, and then relaunch it on a new lease.""",
            },
        ],
    },
    {
        "label": "Instance Creation/Connectivity/Usage",
        "desc": "When submitting a ticket regarding instances, please include the instance ID if possible.",
        "questions": [
            {
                "label": "One of my nodes won't launch",
                "desc": """If you launch multiple nodes at the same time, sometimes the
            service may be overwhelmed. Try launching again, one node at a
            time for any failed nodes.""",
            },
            {
                "label": "The BIOS settings on my instance are incorrect",
                "desc": """If node functionality is not working as expected due to a
            BIOS setting, please submit a ticket letting us know.""",
            },
        ],
    },
    {
        "label": "Jupyter/Trovi",
        "questions": [
            {
                "label": "Error 'The request you have made requires authentication'",
                "desc": """This error can appear if you are using the wrong project
            name. Make sure to update the project ID in the file you are
            running.""",
            },
            {
                "label": "An artifact is not working as expected",
                "desc": """If an artifact isn't working, there may be a few causes. If
            the error message you are seeing is about "not enough resources",
            then the node type configured in the notebook. Check the
            <a href="https://chameleoncloud.org/hardware/">availability calendar</a>
            to see what nodes are free. For other issues, there may be an issue
            with the notebook's itself. In this case, please contact the author
            with specific questions.""",
            },
        ],
    },
    {
        "label": "Account Management",
        "questions": [
            {
                "label": "Linking/Migrating accounts",
                "desc": """For help migrating or linking accounts, please see our
            <a href="https://chameleoncloud.readthedocs.io/en/latest/user/federation/federation_migration.html">migration guide</a>.""",
            }
        ],
    },
]


@login_required
def mytickets(request):
    rt = rtUtil.DjangoRt()
    show_resolved = "show_resolved" in request.GET
    tickets = rt.getUserTickets(request.user.email, show_resolved=show_resolved)
    return render(
        request,
        "djangoRT/ticketList.html",
        {
            "tickets": tickets,
            "show_resolved": show_resolved,
        },
    )


@login_required
def ticketdetail(request, ticket_id):
    rt = rtUtil.DjangoRt()
    ticket = rt.getTicket(ticket_id)
    ticket_history = rt.getTicketHistory(ticket_id)

    # remove bogus "untitled" attachments
    for history in ticket_history:
        history["Attachments"] = [
            a for a in history["Attachments"] if not a[1].startswith("untitled (")
        ]

    return render(
        request,
        "djangoRT/ticketDetail.html",
        {
            "ticket": ticket,
            "ticket_history": ticket_history,
            "ticket_id": ticket_id,
            "hasAccess": rt.hasAccess(ticket_id, request.user.email),
        },
    )


def _handle_ticket_form(request, form):
    """Generic ticket handling helper function.

    If the form is invalid: render an error to the user.
    If the ticket cannot be created: render an error to the user.
    If the ticket could be created but the attachment could not be attached:
        just log an error.

    Args:
        request (Request): The parent request.
        form (Form): The TicketForm to process. It is assumed this already
            has the POST/FILES data attached.

    Returns:
        The ID of the ticket created, if successful. Returns None on error.
    """
    if not form.is_valid():
        messages.error(
            request, "The form is invalid, ensure all required fields are provided."
        )
        return None

    requestor = form.cleaned_data["email"]
    requestor_meta = " ".join(
        [
            form.cleaned_data["first_name"],
            form.cleaned_data["last_name"],
            requestor,
        ]
    )
    header = "\n".join(
        [
            f"[{key}] {value}"
            for key, value in [
                ("Opened by", request.user),
                ("Category", form.cleaned_data["category"]),
                ("Project", form.cleaned_data["project_id"]),
                ("Site", form.cleaned_data["site"]),
                ("Lease ID", form.cleaned_data["lease_id"]),
                ("Instance ID", form.cleaned_data["instance_id"]),
                ("Resource", "Chameleon"),
            ]
        ]
    )

    ticket_body = f"""{header}

    {form.cleaned_data["problem_description"]}

    ---
    {requestor_meta}
    """

    rt = rtUtil.DjangoRt()

    ticket = rtModels.Ticket(
        subject=form.cleaned_data["subject"],
        problem_description=ticket_body,
        requestor=requestor,
        cc=form.cleaned_data.get("cc", []),
    )

    ticket_id = rt.createTicket(ticket)

    if ticket_id < 0:
        logger.error(f"Error creating ticket for {requestor}")
        messages.error(
            request, ("There was an error creating your ticket. Please try again.")
        )
        return None

    logger.info(f"Created ticket #{ticket_id} for {requestor}")

    if "attachment" in request.FILES:
        attachment = request.FILES["attachment"]
        mime_type, encoding = mimetypes.guess_type(attachment.name)
        files = [(attachment.name, attachment, mime_type)]
        success = rt.replyToTicket(ticket_id, files=files)
        if not success:
            logger.error(f"Error adding attachment to #{ticket_id}")

    add_openstack_data.apply_async(
        kwargs={
            "username": request.user.username,
            "ticket_id": ticket_id,
        },
    )

    messages.success(
        request,
        (
            f"Ticket #{ticket_id} has been successfully created. "
            "We will respond to your request as soon as possible."
        ),
    )

    return ticket_id


def ticketcreate(request):
    # Don't require login, be nice and take to guest ticket page.
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("djangoRT:ticketcreateguest"))

    if request.method == "POST":
        form = forms.TicketForm(request.POST, request.FILES)
        ticket_id = _handle_ticket_form(request, form)
        if ticket_id is not None:
            return HttpResponseRedirect(
                reverse("djangoRT:ticketdetail", args=[ticket_id])
            )
    else:
        form = forms.TicketForm(
            initial={
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            }
        )

    return render(
        request,
        "djangoRT/ticketCreate.html",
        {
            "form": form,
            "question_groups": QUESTION_GROUPS,
        },
    )


def ticketcreateguest(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("djangoRT:ticketcreate"))

    if request.method == "POST":
        form = forms.TicketGuestForm(request.POST, request.FILES)
        ticket_id = _handle_ticket_form(request, form)
        if ticket_id is not None:
            # Clear out the form
            form = forms.TicketGuestForm()
            return render(request, "djangoRT/ticketCreateGuest.html", {"form": form})
    else:
        form = forms.TicketGuestForm()

    return render(request, "djangoRT/ticketCreateGuest.html", {"form": form})


@login_required
def ticketreply(request, ticket_id):
    rt = rtUtil.DjangoRt()
    ticket = rt.getTicket(ticket_id)

    if request.method == "POST":
        form = forms.ReplyForm(request.POST, request.FILES)

        if form.is_valid():
            if "attachment" in request.FILES:
                attachment = request.FILES["attachment"]
                mime_type, encoding = mimetypes.guess_type(attachment.name)
                files = [(attachment.name, attachment, mime_type)]
                success = rt.replyToTicket(
                    ticket_id, text=form.cleaned_data["reply"], files=files
                )
                if success:
                    return HttpResponseRedirect(
                        reverse("djangoRT:ticketdetail", args=[ticket_id])
                    )
            else:
                if rt.replyToTicket(ticket_id, text=form.cleaned_data["reply"]):
                    return HttpResponseRedirect(
                        reverse("djangoRT:ticketdetail", args=[ticket_id])
                    )
    else:
        form = forms.ReplyForm()

    return render(
        request,
        "djangoRT/ticketReply.html",
        {
            "ticket_id": ticket_id,
            "ticket": ticket,
            "form": form,
            "hasAccess": rt.hasAccess(ticket_id, request.user.email),
        },
    )


@login_required
def ticketclose(request, ticket_id):
    rt = rtUtil.DjangoRt()
    ticket = rt.getTicket(ticket_id)

    if request.method == "POST":
        form = forms.CloseForm(request.POST)
        if form.is_valid():
            reply = form.cleaned_data["reply"]
            if rt.commentOnTicket(ticket_id, text=reply) and rt.closeTicket(ticket_id):
                return HttpResponseRedirect(
                    reverse("djangoRT:ticketdetail", args=[ticket_id])
                )
    else:
        form = forms.CloseForm()

    return render(
        request,
        "djangoRT/ticketClose.html",
        {
            "ticket_id": ticket_id,
            "ticket": ticket,
            "form": form,
            "hasAccess": rt.hasAccess(ticket_id, request.user.email),
        },
    )


@login_required
def ticketattachment(request, ticket_id, attachment_id):
    title, attachment = rtUtil.DjangoRt().getAttachment(ticket_id, attachment_id)
    content = attachment["Content"]
    content_disposition = attachment["Headers"]["Content-Disposition"]
    content_type = attachment["Headers"]["Content-Type"]

    if content_disposition == "inline":
        return render(
            request,
            "djangoRT/attachment.html",
            {
                "attachment": content,
                "ticket_id": ticket_id,
                "title": title,
            },
        )
    else:
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = content_disposition
        return response
