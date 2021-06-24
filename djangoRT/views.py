from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
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

    if request.user.username:
        region_list = get_region_list(request.user.username)
        openstack_user_data = render_to_string(
            'djangoRT/project_details.txt', {'regions': region_list}
        )
    else:
        openstack_user_data = "\n---\n    No openstack data for anonymous user."

    ticket_body = f"""{header}

    {form.cleaned_data["problem_description"]}

    ---
    {requestor_meta}


    {remove_empty_lines(openstack_user_data)}
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

    return render(request, "djangoRT/ticketCreate.html", {"form": form})


def ticketcreateguest(request):
    if request.user.is_authenticated():
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


def get_region_list(username):
    keycloak_client = KeycloakClient()
    projects = keycloak_client.get_full_user_projects_by_username(username)

    region_list = []
    for region in list(settings.OPENSTACK_AUTH_REGIONS.keys()):
        try:
            region_list.append(get_openstack_data(username, region, projects))
        except Exception as err:
            logger.error(f'Failed to get OpenStack data for region {region}: {err}')
    return region_list


def get_openstack_data(username, region, projects):
    admin_client = admin_ks_client(region)
    admin_sess = admin_session(region)

    current_region = {}
    current_region["name"] = region
    current_region["projects"] = []

    # we know there is only going to be one domain
    domains = list(admin_client.domains.list(name="chameleon"))
    if not domains:
        logger.error('Didn\'t find the domain "chameleon", skipping this site')
        return current_region
    domain_id = domains[0].id

    ks_users_list = list(admin_client.users.list(name=username, domain=domain_id))
    if len(ks_users_list) > 1:
        logger.warning(
            f"Found {len(ks_users_list)} users for {username}, using the first."
        )
    ks_user = ks_users_list[0]

    all_ks_projects = {
        ks_p.name: ks_p
        for ks_p in admin_client.projects.list(domain=domain_id)
    }
    for project in projects:
        charge_code = project["name"]
        # Project doesn't exist for this region
        if charge_code not in all_ks_projects:
            continue
        ks_project_id = all_ks_projects[charge_code].id
        project_qs = Project.objects.filter(charge_code=charge_code)
        project_list = list(project_qs)
        if len(project_list) > 1:
            raise Exception(f"More than one project found with charge code {charge_code}")
        project = project_list[0]

        current_project = {}
        current_project["charge_code"] = project.charge_code
        current_project["id"] = ks_project_id
        current_region["projects"].append(current_project)

        try:
            current_project["leases"] = get_lease_info(admin_sess, ks_user.id, ks_project_id)
        except Exception as err:
            current_project["lease_error"] = True
            logger.error(f"Failed to get leases in {region} for {project.title}: {err}")
        try:
            current_project["servers"] = get_server_info(
                admin_sess, ks_project_id
            )
        except Exception as err:
            current_project["server_error"] = True
            logger.error(
                f"Failed to get active servers in {region} for {project.title}: {err}"
            )

    return current_region


def get_lease_info(sess, user_id, project_id):
    lease_list = []
    blazar = blazar_client.Client(
        "1", service_type="reservation", interface="publicURL", session=sess
    )
    ironic = ironic_client.Client("1", session=sess)
    leases = blazar.lease.list()
    for lease in leases:
        if lease.get("user_id") != user_id or lease.get("project_id") != project_id:
            continue

        # Ignore if more than 3 days out of date
        end_date = parser.parse(lease.get("end_date"))
        date_diff = datetime.utcnow() - end_date
        if date_diff.days > 3:
            continue

        lease_dict = {}
        lease_dict["name"] = lease.get("name")
        lease_dict["status"] = lease.get("status")
        lease_dict["start_date"] = str(parser.parse(lease.get("start_date")))
        lease_dict["end_date"] = str(end_date)
        lease_dict["id"] = lease.get("id")

        lease_dict["hosts"] = []
        resource_map = {r["id"]: r for r in blazar.host.list()}
        for blazar_host in blazar.host.list_allocations():
            if any(res["lease_id"] == lease_dict["id"] for res in blazar_host["reservations"]):
                resource_host = resource_map[blazar_host["resource_id"]]
                host = {
                    "node_name": resource_host["node_name"],
                    "uid": resource_host["uid"],
                    "node_type": resource_host["node_type"]
                }
                node = ironic.node.get(resource_host["uid"])
                host["provision_state"] = node.provision_state
                host["instance_uuid"] = node.instance_uuid
                host["last_error"] = node.last_error
                lease_dict["hosts"].append(host)

        lease_dict["networks"] = []
        resource_map = {r["id"]: r for r in blazar.network.list()}
        for network in blazar.network.list_allocations():
            if any(res["lease_id"] == lease_dict["id"] for res in network["reservations"]):
                lease_dict["networks"].append(resource_map[network["resource_id"]])
        lease_list.append(lease_dict)
    return lease_list


def remove_empty_lines(string):
    return "\n".join([line for line in string.split("\n") if len(line.strip()) > 0])


def get_server_info(sess, project_id):
    server_list = []
    nova = nova_client.Client("2", session=sess)
    glance = glance_client("2", service_type="image", session=sess)
    servers = nova.servers.list(search_opts={"all_tenants": True})
    for server in servers:
        if server.tenant_id != project_id:
            continue
        server_dict = {}
        server_dict["name"] = server.name
        server_dict["status"] = str(server.status)
        server_dict["created_date"] = str(parser.parse(server.created))
        server_dict["id"] = server.id
        server_dict["networks"] = []
        for network in server.addresses.keys():
            network_dict = {"name": network, "addresses": []}
            for address in server.addresses[network]:
                network_dict["addresses"].append(
                    {
                        "addr": address["addr"],
                        "type": address["OS-EXT-IPS:type"],
                    }
                )
            server_dict["networks"].append(network_dict)
        image = glance.images.get(str(server.image["id"]))
        server_dict["image_name"] = str(image.name)
        server_dict["image_id"] = str(image.id)
        server_list.append(server_dict)
    return server_list
