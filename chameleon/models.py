from django.db import models
from django.conf import settings

class UserProperties(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)
    PI_STATUS_CHOICES = (
        ('INELIGIBLE', 'Ineligible'),
        ('ELIGIBLE', 'Eligible'),
    )

    pi_eligibility = models.CharField(max_length=50, blank=False,\
        default='INELIGIBLE', choices=PI_STATUS_CHOICES)
    pi_requested_at = models.DateTimeField('Date Requested', default=None)
    pi_reviewed_at = models.DateTimeField('Date Reviewed', default=None)
    pi_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL,\
        default=None,on_delete=models.CASCADE, related_name='+',)
    pi_decision_summary = models.TextField(default=None)
