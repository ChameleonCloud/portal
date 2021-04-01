from django.db import models
import logging
from django.conf import settings
from projects.models import Project
from util.consts import allocation

logger = logging.getLogger("allocations")


def _format_date(dateobj):
    return dateobj.strftime(allocation.TAS_DATE_FORMAT) if dateobj else None


class Allocation(models.Model):
    STATUS = (
        ("inactive", "expired or overused"),
        ("active", "active"),
        ("pending", "waiting for review decision"),
        ("rejected", "rejected"),
        ("approved", "approved but not active"),
    )
    project = models.ForeignKey(Project, related_name="allocations")
    status = models.CharField(max_length=50, blank=False, choices=STATUS)
    justification = models.TextField(null=True)
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="allocation_requestor", null=True
    )
    date_requested = models.DateTimeField()
    decision_summary = models.TextField(null=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="allocation_reviewer", null=True
    )
    date_reviewed = models.DateTimeField(null=True)
    expiration_date = models.DateTimeField(null=True)
    su_requested = models.FloatField()
    start_date = models.DateTimeField(null=True)
    su_allocated = models.FloatField(null=True)
    su_used = models.FloatField(null=True)

    def as_tas(self):
        return Allocation.to_tas(self)

    @classmethod
    def to_tas(cls, alloc):
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
