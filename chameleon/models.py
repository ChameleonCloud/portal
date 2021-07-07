from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class PIEligibility(models.Model):
    STATUS = [
        ("REQUESTED", "Requested"),
        ("ELIGIBLE", "Eligible"),
        ("INELIGIBLE", "Ineligible"),
    ]
    requestor = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            editable=False,
            on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS, default="REQUESTED")
    review_date = models.DateTimeField(auto_now_add=False, editable=False, null=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        editable=False,
        related_name="+",
        on_delete=models.CASCADE
    )
    review_summary = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "PI Eligibility Request"

    def __str__(self):
        return self.requestor.username

    """
        Overriding so we don't create new PI Eligibility requests for users with one PI Request already pending
    """

    def save(self, *args, **kwargs):
        try:
            # Go ahead and save if we're just updating an existing PIE request
            self.review_date = (
                timezone.now()
            )  # set the review date since we're updating an existing request
            pie_request = PIEligibility.objects.get(id=self.id)
            return super(PIEligibility, self).save(*args, **kwargs)
        except ObjectDoesNotExist:
            pass
        try:
            # Don't save PIE Request if one exists with status requested or eligible
            pie_requests = PIEligibility.objects.filter(
                Q(requestor=self.requestor),
                Q(status="REQUESTED") | Q(status="ELIGIBLE"),
            )
            if pie_requests:
                logger.info(
                    "PI Eligibility request for user {0}, exists, not creating a new one.".format(
                        self.requestor.username
                    )
                )
                return None
        except:
            pass
        # if we're here, this is a new request and no open requests exist, go ahead and create one
        return super(PIEligibility, self).save(*args, **kwargs)
