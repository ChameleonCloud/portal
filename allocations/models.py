from django.db import models
import json
import logging
from django.conf import settings
from datetime import datetime
from projects.models import Project

logger = logging.getLogger('allocations')

class Allocation(models.Model):
    STATUS = (
        ('inactive', 'expired or overused'),
        ('active', 'active'),
        ('pending', 'waiting for review decision'),
        ('rejected', 'rejected'),
        ('approved', 'approved but not active')
    )
    project = models.ForeignKey(Project, related_name='allocations')
    status = models.CharField(max_length=50, blank=False, choices=STATUS)
    justification = models.TextField(null=True)
    requestor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='allocation_requestor', null=True)
    date_requested = models.DateTimeField()
    decision_summary = models.TextField(null=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='allocation_reviewer',null=True)
    date_reviewed = models.DateTimeField(null=True)
    expiration_date = models.DateTimeField(null=True)
    su_requested = models.FloatField()
    start_date = models.DateTimeField(null=True)
    su_allocated = models.FloatField(null=True)
    su_used = models.FloatField(null=True)
    
    def requestor_username(self):
        if self.requestor:
            return self.requestor.username
        else:
            return None

    def requestor_id(self):
        if self.requestor:
            return self.requestor.id
        else:
            return None
    
    def reviewer_username(self):
        if self.reviewer:
            return self.reviewer.username
        else:
            return None
    
    def reviewer_id(self):
        if self.reviewer:
            return self.reviewer.id
        else:
            return None
