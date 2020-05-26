from django.db import models
import json
import logging
from django.conf import settings
from datetime import datetime

logger = logging.getLogger('allocations')

class Allocation(models.Model):
    STATUS = (
        ('inactive', 'expired or overused'),
        ('active', 'active'),
        ('pending', 'waiting for review decision'),
        ('rejected', 'rejected'),
        ('approved', 'approved but not active')
    )
    project_charge_code = models.CharField(max_length=50,blank=False)
    status = models.CharField(max_length=50, blank=False,choices=STATUS)
    justification = models.CharField(max_length=500,null=True)
    requestor = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='allocation_requestor', null=True)
    date_requested = models.DateTimeField(null=True)
    decision_summary = models.CharField(max_length=500,null=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='allocation_reviewer',null=True)
    date_reviewed = models.DateTimeField(null=True)
    expiration_date = models.DateTimeField(null=True)
    su_requested = models.FloatField()
    start_date = models.DateTimeField()
    su_allocated = models.FloatField()
    su_used = models.FloatField(null=True)
    
    def requestor_username(self):
        return self.requestor.username

    def requestor_id(self):
        return self.requestor.id
    
    def reviewer_username(self):
        return self.reviewer.username
    
    def reviewer_id(self):
        return self.reviewer.id
