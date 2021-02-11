import json
import logging
from datetime import datetime

from django.conf import settings
from django.db import models
from projects.models import Project

logger = logging.getLogger("allocations")


class Allocation(models.Model):
    STATUS = (
        ("inactive", "expired or overused"),
        ("active", "active"),
        ("pending", "waiting for review decision"),
        ("rejected", "rejected"),
        ("approved", "approved but not active"),
    )
    project = models.ForeignKey(
        Project,
        related_name="allocations",
        on_delete=models.CASCADE,
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
    su_requested = models.FloatField()
    start_date = models.DateTimeField(null=True)
    su_allocated = models.FloatField(null=True)
    su_used = models.FloatField(null=True)
