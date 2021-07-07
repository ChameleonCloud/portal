import calendar
from datetime import datetime, timedelta
import logging
import pytz
from operator import attrgetter

from celery.decorators import task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.html import strip_tags
from allocations.models import Allocation
from allocations.allocations_api import BalanceServiceClient
from util.keycloak_client import KeycloakClient

LOG = logging.getLogger(__name__)

def warn_user_for_expiring_allocation():
    """
    Sends an email to users when their allocation is within one month of expiring
    """
    now = datetime.now()
    today = now.date()
    days_this_month = calendar.monthrange(today.year, today.month)[1]
    target_expiration_date = today + timedelta(days=days_this_month)

    # Find allocations that are expiring between today and 1 month, and have not been warned of their impending doom
    expiring_allocations = Allocation.objects.filter(status='active',
                                                     expiration_date__lte=target_expiration_date,
                                                     expiration_date__gte=today,
                                                     expiration_warning_issued__isnull=True)
    emails_sent = 0
    for alloc in expiring_allocations:
        charge_code = alloc.project.charge_code
        expiration_date = alloc.expiration_date.date()

        if not expiration_date:
            LOG.debug(f"Allocation {alloc.id} has no expiration date.")
            continue

        time_until_expiration = expiration_date - today

        if expiration_date == today:
            time_description = "today"
        else:
            # "in 1 day" | "in <n> days"
            time_description = f"in {time_until_expiration.days} day{'s' if time_until_expiration.days != 1 else ''}"

        email_body = f"""
        <p>
            The allocation for project <b>{charge_code}</b> will expire <b>{time_description}.</b> 
            See our 
            <a href="https://chameleoncloud.readthedocs.io/en/latest/user/project.html#recharge-or-extend-your-allocation">Documentation</a> 
            on how to recharge or extend your allocation.
        </p>
        """

        mail_error = f"Failed to send expiration warning email for project {charge_code} to {alloc.project.pi.email}"
        try:
            mail_sent = send_mail(
                subject=f"NOTICE: Your allocation for project {charge_code} expires {time_description}!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alloc.project.pi.email],
                message=strip_tags(email_body),
                html_message=email_body,
            )
        except Exception:
            mail_sent = False
            LOG.exception(mail_error)

        # The database transaction is in a separate block of code from sending the mail itself
        # so that we may differentiate between exceptions thrown via sending mail and via updating the database
        if mail_sent:
            emails_sent += 1
            LOG.info(f"Warned PI about allocation {alloc.id} expiring on {alloc.expiration_date}")
            if alloc.expiration_warning_issued:
                LOG.warning(f"Issued a duplicate expiration warning for project {charge_code}.")
            try:
                with transaction.atomic():
                    alloc.expiration_warning_issued = now
                    alloc.save()
            except Exception:
                LOG.error(f"Failed to update ORM with expiration warning timestamp for project {charge_code}.")
        else:
            LOG.error(mail_error)

    LOG.debug(f"Needed to send mail for {len(expiring_allocations)}, and {emails_sent} emails were actually sent.")

def _deactivate_allocation(balance_service, alloc):
    charge_code = alloc.project.charge_code
    balance = balance_service.get_balance(charge_code) or {}
    if 'used' in balance and balance['used']:
        alloc.su_used = float(balance['used'])
    else:
        alloc.su_used = None
        LOG.error(f'Couldn\'t find used balance for project {charge_code}')
    alloc.status = 'inactive'
    alloc.save()
    KeycloakClient().update_project(charge_code, has_active_allocation='false')

def expire_allocations(balance_service):
    now = datetime.now(pytz.utc)

    expired_allocations = Allocation.objects.filter(status='active', expiration_date__lte=now)
    expired_alloc_count = 0
    for alloc in expired_allocations:
        charge_code = alloc.project.charge_code
        try:
            with transaction.atomic():
                # set status to inactive and set the final su_used in portal db
                _deactivate_allocation(balance_service, alloc)
                # reset balance service
                balance_service.reset(charge_code)
                expired_alloc_count = expired_alloc_count + 1
        except Exception:
            LOG.exception(f'Error expiring project {charge_code}')
        LOG.info(f'Expired allocation {alloc.id} for {charge_code}')

    LOG.debug('need to expire {} allocations, and {} were actually expired'.format(len(expired_allocations), expired_alloc_count))

def deactivate_multiple_active_allocations_of_projects():
    for proj_id in Allocation.objects.order_by().values_list('project_id', flat=True).distinct():
        project_active_allocations = list(Allocation.objects.filter(status='active', project_id=proj_id))
        if len(project_active_allocations) > 1:
            LOG.warning(f'project {proj_id} has more than one active allocations')
            by_expiration = sorted(project_active_allocations,
                                   key=attrgetter('expiration_date'), reverse=True)
            # Deactivate any allocations with earlier expiration dates
            for alloc in by_expiration[1:]:
                charge_code = alloc.project.charge_code
                alloc.status = 'inactive'
                alloc.expiration_date = datetime.now(pytz.utc)
                alloc.save()
                LOG.info(f'Deactivated duplicate allocation {alloc.id} for {charge_code}')

def active_approved_allocations(balance_service):
    now = datetime.now(pytz.utc)

    approved_allocations = Allocation.objects.filter(status='approved', start_date__lte=now)
    activated_alloc_count = 0
    for alloc in approved_allocations:
        charge_code = alloc.project.charge_code
        # deactivate active allocation for the project and set status to active
        project_active_allocations = Allocation.objects.filter(status='active', project_id=alloc.project.id)
        prev_alloc = None
        if len(project_active_allocations) > 0:
            prev_alloc = project_active_allocations[0]
        try:
            with transaction.atomic():
                if prev_alloc:
                    _deactivate_allocation(balance_service, prev_alloc)
                alloc.status = 'active'
                alloc.save()
                KeycloakClient().update_project(charge_code, has_active_allocation='true')
                # recharge balance service
                balance_service.recharge(charge_code, alloc.su_allocated)
                activated_alloc_count = activated_alloc_count + 1
        except Exception:
            LOG.exception(f'Error activating project {charge_code}')
        LOG.info(f'Started allocation {alloc.id} for {charge_code}')

    LOG.debug('need to activated {} allocations, and {} were actually activated'.format(len(approved_allocations), activated_alloc_count))

@task
def activate_expire_allocations():
    balance_service = BalanceServiceClient()
    # warn users about allocations expiring within the month
    warn_user_for_expiring_allocation()
    # expire allocations
    expire_allocations(balance_service)
    # check projects with multiple active allocations
    deactivate_multiple_active_allocations_of_projects()
    # activate allocations
    active_approved_allocations(balance_service)
