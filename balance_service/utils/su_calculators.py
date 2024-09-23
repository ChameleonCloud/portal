from django.utils import timezone
from django.db import models
from django.db.models import ExpressionWrapper, F, Sum, functions

from projects.models import Project
from allocations.models import Charge


def get_used_sus(charge):
    now = timezone.now()
    actual_end_time = charge.end_time
    if charge.start_time > now:
        # not started yet
        return 0.0
    if not actual_end_time or actual_end_time > now:
        # ongoing charge
        actual_end_time = now
    time_diff = (actual_end_time - charge.start_time).total_seconds()
    if time_diff < 0:
        return 0.0
    return round(time_diff / 3600.0 * charge.hourly_cost, 2)


def get_total_sus(charge):
    time_diff = (charge.end_time - charge.start_time).total_seconds()
    total_sus = round(time_diff / 3600.0 * charge.hourly_cost, 2)
    return max(total_sus, 0.0)


def get_active_allocation(project):
    return next(project.allocations.filter(status="active").iterator(), None)


def get_consecutive_approved_allocation(project, alloc):
    approved_allocs = project.allocations.filter(
        status="approved",
        start_date__lte=alloc.expiration_date,
        expiration_date__gte=alloc.expiration_date,
    )
    return next(approved_allocs.iterator(), None)


def project_balances(project_ids) -> "list[dict]":
    """Return a list of balance information for each input project.

    Args:
        project_ids (list[int]): A list of project ids.

    Returns:
        A dict structure for each project with ``charge_code`` and the balance
            counters for that project.
    """

    project_balances = []
    for project in Project.objects.filter(pk__in=project_ids):
        active_allocation = get_active_allocation(project)
        used_sus = 0.0
        allocated_sus = 0.0
        if active_allocation:
            allocated_sus = active_allocation.su_allocated
            used_sus = sum(
                [get_used_sus(charge) for charge in active_allocation.charges.all()]
            )
            total_sus = sum(
                [get_total_sus(charge) for charge in active_allocation.charges.all()]
            )
        else:
            allocated_sus = 0.0
            used_sus = 0.0
            total_sus = 0.0
        project_balances.append(
            {
                "id": project.id,
                "charge_code": project.charge_code,
                "used": used_sus,  # how much they have used
                "total": total_sus,  # how much they have used + pending use
                "encumbered": total_sus - used_sus,  # pending use
                "allocated": allocated_sus,
            }
        )
    return project_balances


def calculate_user_total_su_usage(user, project):
    """
    Calculate the current SU usage for the args:user in args:project
    """
    allocation = get_active_allocation(project)
    if not allocation:
        return 0

    charges = Charge.objects.filter(allocation=allocation, user=user)

    # Avoid doing the calculation if there are no charges
    if not charges.exists():
        return 0
    microseconds_per_hour = 1_000_000 * 3600
    # could've used output field as DurationField and further annotate with
    # Extract('charge_duration', 'hour') to get the duration in hours but
    # Extract requires native DurationField database support.
    charges_with_duration_in_ms = charges.annotate(
        charge_duration=ExpressionWrapper(
            F("end_time") - F("start_time"), output_field=models.FloatField()
        )
    )
    # Calculate cost of each charge in SUs by converting ms to hours
    charges_with_actual_cost = charges_with_duration_in_ms.annotate(
        charge_cost=F("charge_duration") / microseconds_per_hour * F("hourly_cost")
    )
    # calculates the total cost of charges for the user on the project
    # by summing up the charge_cost values calculated for each charge.
    # If there are no charges, it returns 0.0
    return charges_with_actual_cost.aggregate(
        total_cost=functions.Coalesce(
            Sum("charge_cost"), 0.0, output_field=models.IntegerField()
        )
    )["total_cost"]
