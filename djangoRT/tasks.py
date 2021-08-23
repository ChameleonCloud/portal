from datetime import datetime

from celery.decorators import task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.template.loader import render_to_string
from djangoRT import rtUtil

from glanceclient import Client as glance_client
from novaclient import client as nova_client
from ironicclient import client as ironic_client
from blazarclient import client as blazar_client
from chameleon.keystone_auth import admin_session, admin_ks_client
from projects.models import Project
from util.keycloak_client import KeycloakClient
from dateutil import parser

LOG = get_task_logger(__name__)


class OpenstackDataError(Exception):
    def __init__(self, messages=[]):
        self.messages = messages
        super(OpenstackDataError, self).__init__(messages)


@task(bind=True)
def add_openstack_data(self, **kwargs):
    ticket_id = kwargs.get("ticket_id")
    username = kwargs.get("username")

    messages = []
    bound_task = self

    def write_message(progress_pct, message):
        LOG.info(message)
        messages.append(message)
        bound_task.update_state(
            state="PROGRESS",
            meta={
                "messages": messages,
                "progress_pct": progress_pct,
            },
        )

    try:
        if username:
            keycloak_client = KeycloakClient()
            projects = keycloak_client.get_full_user_projects_by_username(username)

            regions = list(settings.OPENSTACK_AUTH_REGIONS.keys())
            region_list = []
            for i, region in enumerate(regions):
                try:
                    factor = (1.0 / len(regions)) * 100
                    write_message(factor * i, f'Processing region "{region}"')
                    region_list.append(get_openstack_data(username, region, projects))
                except Exception as err:
                    LOG.error(
                        f"Failed to get OpenStack data for region {region}: {err}"
                    )
            openstack_user_data = remove_empty_lines(
                render_to_string(
                    "djangoRT/project_details.txt", {"regions": region_list}
                )
            )
        else:
            openstack_user_data = "No openstack data for anonymous user."
        rt = rtUtil.DjangoRt()
        rt.commentOnTicket(ticket_id, openstack_user_data)
    except Exception as exc:
        LOG.exception("Failed to gather data")
        exc_message = getattr(exc, "message", None)
        if exc_message:
            messages.append(exc_message)
        raise OpenstackDataError(messages=messages) from exc
    # Return current state as last action
    return {
        "messages": messages,
        "progress_pct": 100.0,
    }


def get_openstack_data(username, region, projects):
    admin_client = admin_ks_client(region)
    admin_sess = admin_session(region)

    current_region = {}
    current_region["name"] = region
    current_region["projects"] = []

    # we know there is only going to be one domain
    domains = list(admin_client.domains.list(name="chameleon"))
    if not domains:
        LOG.error('Didn\'t find the domain "chameleon", skipping this site')
        return current_region
    domain_id = domains[0].id

    ks_users_list = list(admin_client.users.list(name=username, domain=domain_id))
    if len(ks_users_list) > 1:
        LOG.warning(
            f"Found {len(ks_users_list)} users for {username}, using the first."
        )
    ks_user = ks_users_list[0]

    all_ks_projects = {
        ks_p.name: ks_p for ks_p in admin_client.projects.list(domain=domain_id)
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
            raise Exception(
                f"More than one project found with charge code {charge_code}"
            )
        project = project_list[0]

        current_project = {}
        current_project["charge_code"] = project.charge_code
        current_project["id"] = ks_project_id
        current_region["projects"].append(current_project)

        try:
            current_project["leases"] = get_lease_info(
                admin_sess, ks_user.id, ks_project_id
            )
        except Exception as err:
            current_project["lease_error"] = True
            LOG.error(f"Failed to get leases in {region} for {project.title}: {err}")
        try:
            current_project["servers"] = get_server_info(admin_sess, ks_project_id)
        except Exception as err:
            current_project["server_error"] = True
            LOG.error(
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
            if any(
                res["lease_id"] == lease_dict["id"]
                for res in blazar_host["reservations"]
            ):
                resource_host = resource_map[blazar_host["resource_id"]]
                host = {
                    "node_name": resource_host["node_name"],
                    "uid": resource_host["uid"],
                    "node_type": resource_host["node_type"],
                }
                node = ironic.node.get(resource_host["uid"])
                host["provision_state"] = node.provision_state
                host["instance_uuid"] = node.instance_uuid
                host["last_error"] = node.last_error
                lease_dict["hosts"].append(host)

        lease_dict["networks"] = []
        resource_map = {r["id"]: r for r in blazar.network.list()}
        for network in blazar.network.list_allocations():
            if any(
                res["lease_id"] == lease_dict["id"] for res in network["reservations"]
            ):
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
