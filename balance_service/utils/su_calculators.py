from django.utils import timezone

from projects.models import Project


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
        project_balances.append(
            {
                "id": project.id,
                "charge_code": project.charge_code,
                "used": used_sus,
                "total": total_sus,
                "encumbered": total_sus - used_sus,
                "allocated": allocated_sus,
            }
        )
    return project_balances
