import logging

from django.conf import settings
from django.db import models
from django.db.models import ExpressionWrapper, F, Sum, functions
from django.core.validators import MinValueValidator
from balance_service.utils import su_calculators
from projects.models import Project
from util.consts import allocation

logger = logging.getLogger("allocations")


def _format_date(dateobj):
    return dateobj.strftime(allocation.JSON_DATE_FORMAT) if dateobj else None


class Allocation(models.Model):
    STATUS = (
        ("inactive", "expired or overused"),
        ("active", "active"),
        ("pending", "waiting for review decision"),
        ("waiting", "collecting more information from the PI"),
        ("rejected", "rejected"),
        ("approved", "approved but not active"),
    )
    project = models.ForeignKey(
        Project, related_name="allocations", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=50, blank=False, choices=STATUS)
    justification = models.TextField(null=True)
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="allocation_requestor",
        null=True,
        on_delete=models.CASCADE,
    )
    date_requested = models.DateTimeField()
    decision_summary = models.TextField(null=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="allocation_reviewer",
        null=True,
        on_delete=models.CASCADE,
    )
    date_reviewed = models.DateTimeField(null=True)
    expiration_date = models.DateTimeField(null=True)
    expiration_warning_issued = models.DateTimeField(null=True)
    su_requested = models.FloatField()
    start_date = models.DateTimeField(null=True)
    su_allocated = models.FloatField(null=True)
    su_used = models.FloatField(null=True)
    balance_service_version = models.IntegerField(default=2, null=False)

    def as_dict(self):
        return Allocation.to_dict(self)

    @classmethod
    def to_dict(cls, alloc):
        return {
            "computeUsed": alloc.su_used,
            "computeAllocated": alloc.su_allocated,
            "computeRequested": alloc.su_requested,
            "dateRequested": _format_date(alloc.date_requested),
            "dateReviewed": _format_date(alloc.date_reviewed),
            "decisionSummary": alloc.decision_summary,
            "end": _format_date(alloc.expiration_date),
            "id": alloc.id,
            "justification": alloc.justification,
            "memoryUsed": 0,
            "memoryAllocated": 0,
            "memoryRequested": 0,
            "project": alloc.project.charge_code,
            "projectId": -1,
            "requestor": alloc.requestor.username if alloc.requestor else None,
            "requestorId": alloc.requestor_id,
            "resource": "Chameleon",
            "resourceId": 0,
            "reviewer": alloc.reviewer.username if alloc.reviewer else None,
            "reviewerId": alloc.reviewer_id,
            "start": _format_date(alloc.start_date),
            "status": alloc.status.capitalize(),
            "storageUsed": 0,
            "storageAllocated": 0,
            "storageRequested": 0,
        }


class Charge(models.Model):
    allocation = models.ForeignKey(
        Allocation, related_name="charges", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="charges",
        on_delete=models.CASCADE,
    )
    region_name = models.TextField(blank=False)
    resource_id = models.TextField(blank=False)
    resource_type = models.TextField(blank=False)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    hourly_cost = models.FloatField()

    def __str__(self):
        return f"{self.allocation.project}: {self.start_time}-{self.end_time}"


class ChargeBudget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="projectbudgets",
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE
    )
    su_budget = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('user', 'project',)

    def current_usage(self):
        """
        Calculate the current charge usage for the user on this project
        """
        allocation = su_calculators.get_active_allocation(self.project)
        if not allocation:
            return 0

        charges = Charge.objects.filter(allocation=allocation, user=self.user)

        # Avoid doing the calculation if there are no charges
        if not charges.exists():
            return 0
        microseconds_per_hour = 1_000_000 * 3600
        # could've used output field as DurationField and further annotate with
        # Extract('charge_duration', 'hour') to get the duration in hours but
        # Extract requires native DurationField database support.
        charges_with_duration_in_ms = charges.annotate(
            charge_duration=ExpressionWrapper(
                F('end_time') - F('start_time'), output_field=models.FloatField()
            )
        )
        # Calculate cost of each charge in SUs by converting ms to hours
        charges_with_actual_cost = charges_with_duration_in_ms.annotate(
            charge_cost=F('charge_duration') / microseconds_per_hour * F('hourly_cost')
        )
        # calculates the total cost of charges for the user on the project
        # by summing up the charge_cost values calculated for each charge.
        # If there are no charges, it returns 0.0
        return charges_with_actual_cost.aggregate(
            total_cost=functions.Coalesce(Sum('charge_cost'), 0.0, output_field=models.IntegerField())
        )['total_cost']

    def su_left(self):
        return self.su_budget - self.current_usage()
