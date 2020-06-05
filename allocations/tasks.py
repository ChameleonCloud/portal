from __future__ import absolute_import, unicode_literals

from datetime import datetime
import logging
import pytz
from operator import attrgetter

from celery import task
from django.db import transaction
from allocations.models import Allocation
from allocations.allocations_api import BalanceServiceClient

logger = logging.getLogger(__name__)

def expire_allocations(balance_service):
    now = datetime.now(pytz.utc)

    expired_allocations = Allocation.objects.filter(status='active', expiration_date__lte=now)
    expired_alloc_count = 0
    for alloc in expired_allocations:
        try:
            with transaction.atomic():
                # set status to inactive and set the final su_used in portal db
                alloc.su_used = float(balance_service.call(alloc.project_charge_code)['used'])
                alloc.status = 'inactive'
                alloc.save()
                # reset balance service
                balance_service.reset(alloc.project_charge_code)
                expired_alloc_count = expired_alloc_count + 1
        except Exception:
            logger.exception('Error expiring project {}'.format(alloc.project_charge_code))

    logger.debug('need to expire {} allocations, and {} were actually expired'.format(len(expired_allocations), expired_alloc_count))

def deactivate_multiple_active_allocations_of_projects():
    for proj in Allocation.objects.order_by().values_list('project_charge_code', flat=True).distinct():
        project_active_allocations = list(Allocation.objects.filter(status='active', project_charge_code=proj))
        if len(project_active_allocations) > 1:
            logger.warning('project {} has more than one active allocations'.format(proj))
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
        # deactivate active allocation for the project and set status to active
        project_active_allocations = Allocation.objects.filter(status='active', project_charge_code=alloc.project_charge_code)
        proj_alloc = None
        if len(project_active_allocations) > 0:
            proj_alloc = project_active_allocations[0]
        try:
            with transaction.atomic():
                if proj_alloc:
                    proj_alloc.su_used = float(balance_service.call(alloc.project_charge_code)['used'])
                    proj_alloc.status = 'inactive'
                    proj_alloc.save()
                alloc.status = 'active'
                alloc.save()
                # recharge balance service
                balance_service.recharge(alloc.project_charge_code, alloc.su_allocated)
                activated_alloc_count = activated_alloc_count + 1
        except Exception:
            logger.exception('Error activating project {}'.format(alloc.project_charge_code))

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
