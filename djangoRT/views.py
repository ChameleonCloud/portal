import logging
import mimetypes

from blazarclient import client as blazar_client
from chameleon.keystone_auth import admin_ks_client, get_user, project_scoped_session
from dateutil import parser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from glanceclient import Client as glance_client
from novaclient import client as nova_client

from djangoRT import forms, rtModels, rtUtil

logger = logging.getLogger("default")


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

    rt = rtUtil.DjangoRt()

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
                ("Resource", "Chameleon"),
            ]
        ]
    )

    ticket_body = f"""{header}

    {form.cleaned_data["problem_description"]}

    ---
    {requestor_meta}
    """

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
    if not request.user.is_authenticated():
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
        {"form": form, "recaptcha_action": "ticket/new"},
    )


def ticketcreateguest(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("djangoRT:ticketcreate"))

    if request.method == "POST":
        form = forms.TicketGuestForm(request.POST, request.FILES)
        ticket_id = _handle_ticket_form(request, form)
        if ticket_id is not None:
            # Clear out the form
            form = forms.TicketGuestForm()
            return render(
                request,
                "djangoRT/ticketCreateGuest.html",
                {"form": form, "recaptcha_action": "ticket/new/guest"},
            )
    else:
        form = forms.TicketGuestForm()

    return render(
        request,
        "djangoRT/ticketCreateGuest.html",
        {"form": form, "recaptcha_action": "ticket/new/guest"},
    )


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


def get_openstack_data(username, unscoped_token, region):
    current_region = {}
    current_region["name"] = region
    current_region["projects"] = []
    ks_admin = admin_ks_client(region=region)
    ks_user = get_user(ks_admin, username)
    projects = []
    if ks_user:
        projects = ks_admin.projects.list(user=ks_user)
    for project in projects:
        current_project = {}
        current_project["name"] = project.name
        current_project["id"] = project.id
        current_region["projects"].append(current_project)
        try:
            psess = project_scoped_session(
                unscoped_token=unscoped_token, project_id=project.id, region=region
            )
        except Exception:
            logger.error(
                (
                    f"Failed to authenticate to {region} as user {username}, "
                    "skipping data collection"
                )
            )
            continue
        try:
            current_project["leases"] = get_lease_info(psess)
        except Exception as err:
            logger.error(f"Failed to get leases in {region} for {project.name}: {err}")
        try:
            current_project["servers"] = get_server_info(psess)
        except Exception as err:
            logger.error(
                f"Failed to get active servers in {region} for {project.name}: {err}"
            )
    return current_region


def get_lease_info(psess):
    lease_list = []
    blazar = blazar_client.Client(
        "1", service_type="reservation", interface="publicURL", session=psess
    )
    leases = blazar.lease.list()
    for lease in leases:
        lease_dict = {}
        lease_dict["name"] = lease.get("name")
        lease_dict["status"] = lease.get("status")
        lease_dict["start_date"] = str(parser.parse(lease.get("start_date")))
        lease_dict["end_date"] = str(parser.parse(lease.get("end_date")))
        lease_dict["id"] = lease.get("id")
        lease_list.append(lease_dict)
    return lease_list


def get_server_info(psess):
    server_list = []
    nova = nova_client.Client("2", session=psess)
    glance = glance_client("2", service_type="image", session=psess)
    servers = nova.servers.list()
    for server in servers:
        server_dict = {}
        server_dict["name"] = server.name
        server_dict["status"] = str(server.status)
        server_dict["created_date"] = str(parser.parse(server.created))
        server_dict["id"] = server.id
        image = glance.images.get(str(server.image["id"]))
        server_dict["image_name"] = str(image.name)
        server_dict["image_id"] = str(image.id)
        server_list.append(server_dict)
    return server_list
