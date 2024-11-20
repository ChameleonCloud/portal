import calendar
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import pytz
from operator import attrgetter

from celery.decorators import task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.html import strip_tags
from django.urls import reverse
from keycloak.exceptions import KeycloakClientError

from allocations.models import Allocation, Charge
from balance_service.utils.su_calculators import project_balances
from balance_service.enforcement.usage_enforcement import TMP_RESOURCE_ID_PREFIX
from projects.models import Project
from util.keycloak_client import KeycloakClient

from . import utils

LOG = logging.getLogger(__name__)


def _send_expiration_warning_mail(alloc, today):
    """
    For a single allocation, send warning email to its project's PI
    """
    assert alloc.expiration_warning_issued is None

    charge_code = alloc.project.charge_code
    email = alloc.project.pi.email
    expiration_date = alloc.expiration_date.date()

    # Edge cases
    if not expiration_date:
        LOG.warning(f"Allocation {alloc.id} has no expiration date.")
        return None

    if not email:
        LOG.warning(
            f"PI for project {charge_code} has no email; "
            "cannot send expiration warning"
        )
        return None

    time_until_expiration = expiration_date - today

    # Little string to describe the expiration to make the email look nicer
    if expiration_date == today:
        time_description = "today"
    else:
        # "in 1 day" | "in <n> days"
        time_description = (
            f"in {time_until_expiration.days} "
            f"day{'s' if time_until_expiration.days != 1 else ''}"
        )

    project_url = f'https://chameleoncloud.org{reverse("projects:view_project", args=[alloc.project.id])}'
    docs_url = (
        "https://chameleoncloud.readthedocs.io/en/latest/user/project.html"
        "#recharge-or-extend-your-allocation "
    )
    email_body = f"""
            <p>
                The allocation for project <a href="{project_url}"><b>{charge_code}</b></a>
                will expire <b>{time_description}.</b> See our
                <a href={docs_url}>Documentation</a>
                on how to recharge or extend your allocation.
            </p>
            """

    mail_sent = None
    try:
        mail_sent = send_mail(
            subject=f"NOTICE: Your allocation for project {charge_code} "
            f"expires {time_description}!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            message=strip_tags(" ".join(email_body.split()).strip()),
            html_message=email_body,
        )
    except Exception:
        pass

    return mail_sent


@task
def warn_user_for_expiring_allocation():
    """
    Sends an email to users when their allocation is within one month of expiring
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    days_this_month = calendar.monthrange(today.year, today.month)[1]
    target_expiration_date = today + timedelta(days=days_this_month)

    # Find allocations that are expiring between today and 1 month,
    # and have not been warned of their impending doom
    expiring_allocations = Allocation.objects.filter(
        status="active",
        expiration_date__lte=target_expiration_date,
        expiration_date__gte=today,
        expiration_warning_issued__isnull=True,
    )

    emails_sent = 0
    for alloc in expiring_allocations:
        mail_sent = _send_expiration_warning_mail(alloc, today)
        charge_code = alloc.project.charge_code

        # If we successfully sent mail, log it in the database
        if mail_sent:
            emails_sent += 1
            LOG.info(
                f"Warned PI about allocation {alloc.id} "
                f"expiring on {alloc.expiration_date}"
            )
            try:
                with transaction.atomic():
                    alloc.expiration_warning_issued = now
                    alloc.save()
            except Exception:
                LOG.error(
                    f"Failed to update ORM with expiration warning timestamp "
                    f"for project {charge_code}."
                )
        else:
            LOG.error(
                f"Failed to send expiration warning email for project {charge_code}"
            )

    LOG.debug(
        f"Needed to send mail for {len(expiring_allocations)}, "
        f"and {emails_sent} emails were actually sent."
    )


def _deactivate_allocation(alloc):
    balance = project_balances([alloc.project.id])
    if not balance:
        alloc.su_used = None
        LOG.error(f"Couldn't find used balance for project {alloc.project.charge_code}")
    else:
        balance = balance[0]
        alloc.su_used = balance["used"]
    LOG.info(
        f"Deactivating allocation {alloc.id} for project {alloc.project.charge_code}"
    )
    alloc.status = "inactive"
    alloc.save()
    keycloak_client = KeycloakClient()
    keycloak_client.update_project(
        alloc.project.charge_code, has_active_allocation="false"
    )
    updated_project = keycloak_client._lookup_group(alloc.project.charge_code)
    LOG.info(
        f"Project {alloc.project.charge_code} should NOT have active allocation in Keycloak: "
        f"{updated_project.get('attributes')}"
    )


def _fork_charge(charge, split_datetime, new_allocation):
    """Fork charge and assign to new allocation"""
    # end original charge by setting the new end time
    original_end_time = charge.end_time
    charge.end_time = split_datetime
    charge.save()

    # create a new charge by duplicating the old one
    # set a new allocation to the new charge
    # set the new charge start time
    charge.pk = None
    charge._state.adding = True
    charge.allocation = new_allocation
    charge.start_time = max(split_datetime, charge.start_time)
    charge.end_time = original_end_time
    charge.save()


def expire_allocations():
    now = timezone.now()

    expired_allocations = Allocation.objects.filter(
        status="active", expiration_date__lte=now
    )
    expired_alloc_count = 0
    for alloc in expired_allocations:
        charge_code = alloc.project.charge_code
        try:
            with transaction.atomic():
                # set status to inactive and set the final su_used in portal db
                _deactivate_allocation(alloc)
                expired_alloc_count = expired_alloc_count + 1
        except Exception:
            LOG.exception(f"Error expiring project {charge_code}")
        LOG.info(f"Expired allocation {alloc.id} for {charge_code}")

    LOG.debug(
        "need to expire {} allocations, and {} were actually expired".format(
            len(expired_allocations), expired_alloc_count
        )
    )


def deactivate_multiple_active_allocations_of_projects():
    active_allocs = Allocation.objects.filter(status="active")
    project_allocations = defaultdict(list)
    for alloc in active_allocs:
        project_allocations[alloc.project_id].append(alloc)

    for proj_id in project_allocations.keys():
        project_active_allocations = project_allocations[proj_id]
        if len(project_active_allocations) > 1:
            LOG.warning(f"project {proj_id} has more than one active allocations")
            by_expiration = sorted(
                project_active_allocations,
                key=attrgetter("expiration_date"),
                reverse=True,
            )
            # Deactivate any allocations with earlier expiration dates
            for alloc in by_expiration[1:]:
                charge_code = alloc.project.charge_code
                alloc.status = "inactive"
                alloc.expiration_date = datetime.now(pytz.utc)
                alloc.save()
                LOG.info(
                    f"Deactivated duplicate allocation {alloc.id} for {charge_code}"
                )


def active_approved_allocations():
    now = timezone.now()

    approved_allocations = Allocation.objects.filter(
        status="approved", start_date__lte=now
    )
    activated_alloc_count = 0
    for alloc in approved_allocations:
        charge_code = alloc.project.charge_code
        # deactivate active allocation for the project and set status to active
        project_active_allocations = Allocation.objects.filter(
            status="active", project_id=alloc.project.id
        )
        prev_alloc = None
        if len(project_active_allocations) > 0:
            prev_alloc = project_active_allocations[0]
        try:
            with transaction.atomic():
                if prev_alloc:
                    _deactivate_allocation(prev_alloc)
                    allocation_charges = Charge.objects.filter(
                        allocation__id=prev_alloc.id
                    )
                    # duplicate the ongoing charges
                    for c in allocation_charges:
                        if c.end_time > now:
                            _fork_charge(c, now, alloc)
                LOG.info(f"Activating allocation {alloc.id} for project {charge_code}")
                alloc.status = "active"
                alloc.save()
                keycloak_client = KeycloakClient()
                keycloak_client.update_project(
                    charge_code, has_active_allocation="true"
                )

                updated_project = keycloak_client._lookup_group(charge_code)
                LOG.info(
                    f"Project {charge_code} should have active allocation in Keycloak: "
                    f"{updated_project.get('attributes')}"
                )

                activated_alloc_count = activated_alloc_count + 1
        except Exception:
            LOG.exception(f"Error activating project {charge_code}")
        LOG.info(f"Started allocation {alloc.id} for {charge_code}")

    LOG.debug(
        "need to activated {} allocations, and {} were actually activated".format(
            len(approved_allocations), activated_alloc_count
        )
    )


@task
def activate_expire_allocations():
    # expire allocations
    expire_allocations()
    # check projects with multiple active allocations
    deactivate_multiple_active_allocations_of_projects()
    # activate allocations
    active_approved_allocations()
    # check consistency between allocation system and Keycloak
    check_keycloak_consistency()


def _fill_charge_tmp_resource_ids():
    charge_by_region = defaultdict(list)
    for charge in Charge.objects.filter(resource_id__startswith=TMP_RESOURCE_ID_PREFIX):
        charge_by_region[charge.region_name].append(charge)

    for region in charge_by_region.keys():
        db = utils.connect_to_region_db(region)
        for charge in charge_by_region[region]:
            items = charge.resource_id.split("/", maxsplit=4)
            project_id = items[1]
            user_id = items[2]
            lease_start_date = items[3]
            name = items[4]
            resource_type = charge.resource_type
            resource_id = utils.get_resource_id(
                db, project_id, user_id, lease_start_date, resource_type, name
            )
            if resource_id:
                charge.resource_id = resource_id
                charge.save()
            else:
                charge_dict = model_to_dict(charge)
                LOG.error(f"Fail to find resource id for charge: {charge_dict}")
                if charge.allocation.balance_service_version == 1:
                    LOG.info(
                        f"The allocation uses v1 balance service, removing charge {charge_dict}"
                    )
                    charge.delete()


def check_keycloak_consistency():
    active_projects = {
        alloc.project.charge_code
        for alloc in Allocation.objects.filter(status="active")
    }
    inactive_projects = set(
        project.charge_code
        for project in Project.objects.filter(~Q(charge_code__in=active_projects))
    )

    LOG.info(f"CONSISTENCY: {len(active_projects)} active allocations")
    LOG.info(f"CONSISTENCY: {len(inactive_projects)} inactive allocations")

    keycloak_client = KeycloakClient()
    groups = keycloak_client._project_admin()
    groups_url = groups._client.get_full_url(
        groups.get_path("collection", realm=keycloak_client.realm_name)
    )

    active_groups = {
        group.get("name")
        for group in groups._client.get(url=groups_url, briefRepresentation=False)
        # Filter for any groups with have `has_active_allocation` == "true"
        if "true" in group.get("attributes", {}).get("has_active_allocation", [])
    }
    inactive_groups = {
        group.get("name")
        for group in groups._client.get(url=groups_url, briefRepresentation=False)
        # Filter for any groups with have `has_active_allocation` == "false" or None
        if any(
            inactive in group.get("attributes", {}).get("has_active_allocation", [])
            for inactive in ("false", None)
        )
    }

    LOG.info(f"CONSISTENCY: {len(active_groups)} active groups in Keycloak")
    LOG.info(f"CONSISTENCY: {len(inactive_groups)} inactive groups in Keycloak")

    for project in active_projects:
        if project in inactive_groups:
            LOG.warning(
                f"CONSISTENCY: Project {project} with active allocation not active in Keycloak"
            )
            try:
                keycloak_client.update_project(project, has_active_allocation="true")
            except KeycloakClientError:
                # If there are many errors to correct, the client may expire
                LOG.warning(f"Failed to update project {project} in Keycloak. Retrying")
                keycloak_client = KeycloakClient()
                keycloak_client.update_project(project, has_active_allocation="true")

    for project in inactive_projects:
        if project in active_groups:
            LOG.warning(
                f"CONSISTENCY: Project {project} without active allocation is active in Keycloak"
            )
            try:
                keycloak_client.update_project(project, has_active_allocation="false")
            except KeycloakClientError:
                # If there are many errors to correct, the client may expire
                LOG.warning(f"Failed to update project {project} in Keycloak. Retrying")
                keycloak_client = KeycloakClient()
                keycloak_client.update_project(project, has_active_allocation="false")


@task
def check_charge():
    """
    Check if the charges of the active allocations are in sync
    with the actual state of openstack databases
    """
    # openstack db overwrites records for updated leases, so we
    # only compare the end time and the latest hourly cost of a
    # reservation to alert on potential over-charging.

    _fill_charge_tmp_resource_ids()

    compare_content = defaultdict(lambda: defaultdict(dict))
    for alloc in Allocation.objects.filter(status="active"):
        for charge in alloc.charges.all():
            region = charge.region_name
            resource_id = charge.resource_id

            end_time = compare_content[region][resource_id].get("end_time")
            if not end_time or end_time > charge.end_time:
                compare_content[region][resource_id] = {
                    "end_time": charge.end_time,
                    "hourly_cost": charge.hourly_cost,
                }
    # fetch info from openstack db
    for region in compare_content.keys():
        db = utils.connect_to_region_db(region)
        region_resources = compare_content[region]

        openstack_records = []
        resource_ids = list(region_resources.keys())
        openstack_records.extend(utils.get_computehost_charges_by_ids(db, resource_ids))
        openstack_records.extend(utils.get_network_charges_by_ids(db, resource_ids))
        openstack_records.extend(utils.get_floatingip_charges_by_ids(db, resource_ids))

        for openstack_r in openstack_records:
            resource_id = openstack_r.get("resource_id")
            portal_r = region_resources.get(resource_id)
            openstack_endtime = openstack_r.get("end_time")
            portal_endtime = portal_r.get("end_time").strftime(utils.DATETIME_FORMAT)
            if openstack_endtime != portal_endtime:
                pass
                # LOG.error(
                #     f"{resource_id} at {region} has incorrect end time! "
                #     f"openstack={openstack_endtime}, portal={portal_endtime}"
                # )
            openstack_cost = openstack_r.get("hourly_cost")
            portal_cost = float(portal_r.get("hourly_cost"))
            if openstack_cost != portal_cost:
                pass
                # LOG.error(
                #     f"{resource_id} at {region} has incorrect hourly cost! "
                #     f"openstack={openstack_cost}, portal={portal_cost}"
                # )
