from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

class UserProperties(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True)

    class Meta:
        verbose_name = ("User Properties")
        verbose_name_plural = ("User Properties")

    def pi_eligibility():
        try:
            return PIEligibility.objects.filter(requestor=self).latest('request_date').status
        except ObjectDoesNotExist:
            return 'Ineligible'


class PIEligibility(models.Model):
    STATUS = [
        ('REQUESTED', 'Requested'),
        ('ELIGIBLE', 'Eligible'),
        ('INELIGIBLE', 'Ineligible'),
    ]
    requestor = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    request_date = models.DateTimeField(auto_now_add=True)
    status =  models.CharField(max_length=10, choices=STATUS, default='REQUESTED')
    review_date = models.DateTimeField(auto_now_add=False, editable=False, null=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, editable=False, related_name='+')
    review_summary = models.TextField(blank=True,null=True)

    class Meta:
        verbose_name = ("PI Eligibility Request")

    def __unicode__(self):
        return self.requestor.username

    '''
        Overriding so we don't create new PI Eligibility requests for users with one PI Request already pending
    '''
    def save(self, *args, **kwargs):
        try:
            # Go ahead and save if we're just updating an existing PIE request
            pie_request = PIEligibility.objects.get(id=self.id)
            return super(PIEligibility, self).save(*args, **kwargs)
        except ObjectDoesNotExist:
            pass
        try:
            # Don't save PIE Request if one exists with status requested or eligible
            pie_requests = PIEligibility.objects.filter(Q(requestor=self.requestor),Q(status='REQUESTED') | Q(status='ELIGIBLE'))
            if pie_requests:
                return None
        except:
            pass
        return super(PIEligibility, self).save(*args, **kwargs)
