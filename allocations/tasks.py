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
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.html import strip_tags
from allocations.allocations_api import BalanceServiceClient
from allocations.models import Allocation, Charge
from balance_service.utils.su_calculators import project_balances
from balance_service.enforcement.usage_enforcement import TMP_RESOURCE_ID_PREFIX
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

    docs_url = (
        "https://chameleoncloud.readthedocs.io/en/latest/user/project.html"
        "#recharge-or-extend-your-allocation "
    )
    email_body = f"""
            <p>
                The allocation for project <b>{charge_code}</b>
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
        status='active',
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
    alloc.status = "inactive"
    alloc.save()
    KeycloakClient().update_project(
        alloc.project.charge_code, has_active_allocation="false"
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


def expire_allocations(balance_service):
    now = timezone.now()

    expired_allocations = Allocation.objects.filter(
        status='active', expiration_date__lte=now
    )
    expired_alloc_count = 0
    for alloc in expired_allocations:
        charge_code = alloc.project.charge_code
        try:
            with transaction.atomic():
                # set status to inactive and set the final su_used in portal db
                _deactivate_allocation(alloc)
                # TODO: remove reset external balance service
                # after retiring redis
                balance_service.reset(charge_code)
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


def active_approved_allocations(balance_service):
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
                alloc.status = "active"
                alloc.save()
                # TODO: remove recharge external balance service
                # after retiring redis
                balance_service.recharge(charge_code, alloc.su_allocated)
                KeycloakClient().update_project(
                    charge_code, has_active_allocation="true"
                )

                activated_alloc_count = activated_alloc_count + 1
        except Exception:
            LOG.exception(f'Error activating project {charge_code}')
        LOG.info(f'Started allocation {alloc.id} for {charge_code}')

    LOG.debug('need to activated {} allocations, and {} were actually activated'.format(len(approved_allocations), activated_alloc_count))


@task
def activate_expire_allocations():
    balance_service = BalanceServiceClient()
    # expire allocations
    expire_allocations(balance_service)
    # check projects with multiple active allocations
    deactivate_multiple_active_allocations_of_projects()
    # activate allocations
    active_approved_allocations(balance_service)


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
            if openstack_r.get("end_time") != portal_r.get("end_time").strftime(
                utils.DATETIME_FORMAT
            ):
                LOG.error(f"{resource_id} at {region} has incorrect end time!")
            if float(openstack_r.get("hourly_cost")) != float(
                portal_r.get("hourly_cost")
            ):
                LOG.error(f"{resource_id} at {region} has incorrect hourly cost!")
