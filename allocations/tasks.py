

from datetime import datetime
import logging
import pytz
from operator import attrgetter

from celery.decorators import task
from django.db import transaction
from allocations.models import Allocation
from allocations.allocations_api import BalanceServiceClient
from util.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)

def _deactivate_allocation(balance_service, alloc):
    charge_code = alloc.project.charge_code
    balance = balance_service.get_balance(charge_code) or {}
    if 'used' in balance and balance['used']:
        alloc.su_used = float(balance['used'])
    else:
        alloc.su_used = None
        logger.error(f'Couldn\'t find used balance for project {charge_code}')
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
            logger.exception(f'Error expiring project {charge_code}')

    logger.debug('need to expire {} allocations, and {} were actually expired'.format(len(expired_allocations), expired_alloc_count))

def deactivate_multiple_active_allocations_of_projects():
    for proj_id in Allocation.objects.order_by().values_list('project_id', flat=True).distinct():
        project_active_allocations = list(Allocation.objects.filter(status='active', project_id=proj_id))
        if len(project_active_allocations) > 1:
            logger.warning(f'project {proj_id} has more than one active allocations')
            by_expiration = sorted(project_active_allocations,
                                   key=attrgetter('expiration_date'), reverse=True)
            # Deactivate any allocations with earlier expiration dates
            for alloc in by_expiration[1:]:
                alloc.status = 'inactive'
                alloc.save()

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
            logger.exception(f'Error activating project {charge_code}')

    logger.debug('need to activated {} allocations, and {} were actually activated'.format(len(approved_allocations), activated_alloc_count))

@task
def activate_expire_allocations():
    balance_service = BalanceServiceClient()
    # expire allocations
    expire_allocations(balance_service)
    # check projects with multiple active allocations
    deactivate_multiple_active_allocations_of_projects()
    # activate allocations
    active_approved_allocations(balance_service)
