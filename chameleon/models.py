from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PIEligibility(models.Model):
    STATUS = [
        ("REQUESTED", "Requested"),
        ("ELIGIBLE", "Eligible"),
        ("INELIGIBLE", "Ineligible"),
    ]
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL, editable=False, on_delete=models.CASCADE
    )
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS, default="REQUESTED")
    review_date = models.DateTimeField(auto_now_add=False, editable=False, null=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        editable=False,
        related_name="+",
        on_delete=models.CASCADE,
    )
    review_summary = models.TextField(blank=True, null=True)
    department_directory_link = models.URLField(max_length=500, blank=True, null=True)
    ticket_id = models.CharField(max_length=100, null=True, blank=True)

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


class Institution(models.Model):
    class Source(models.TextChoices):
        CANONICAL = "canonical", "Canonical list"
        AI = "ai", "AI generated"
        MANUAL = "manual", "Manually entered"

    class InstitutionType(models.TextChoices):
        R1 = "r1", "R1 University"
        R2 = "r2", "R2 University"
        COMMUNITY_COLLEGE = "cc", "Community College"
        GOVERNMENT = "gov", "Government"
        NONPROFIT = "nonprofit", "Nonprofit"
        INDUSTRY = "industry", "Industry"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=500)

    # metadata
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.CANONICAL,
    )
    source_comment = models.TextField(blank=True)

    # location
    state = models.CharField(max_length=100, blank=True)  # "n/a" if not US

    # classification
    institution_type = models.CharField(
        max_length=20,
        choices=InstitutionType.choices,
        default=InstitutionType.UNKNOWN,
    )

    minority_serving_institution = models.BooleanField(default=False)
    epscor_state = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # External identifiers
    ipeds_unitid = models.CharField(max_length=20, null=True, blank=True, unique=True)
    ror_id = models.CharField(max_length=100, null=True, blank=True, unique=True)

    # Carnegie classification (from IPEDS C18BASIC), e.g. "R1", "R2", "Associate's"
    carnegie_classification = models.CharField(max_length=100, blank=True)

    # Public vs. private (from IPEDS CONTROL)
    class Control(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE_NONPROFIT = "private_nonprofit", "Private Non-profit"
        PRIVATE_FORPROFIT = "private_forprofit", "Private For-profit"

    control = models.CharField(max_length=20, choices=Control.choices, blank=True)

    # Country code for international institutions (default US)
    country = models.CharField(max_length=100, default="US")

    # City (from ACE city column or ROR geonames)
    city = models.CharField(max_length=200, blank=True)

    # Geolocation for mapping (from ROR geonames)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Full Carnegie classification text, e.g. "Doctoral Universities: Very High Research Activity"
    carnegie_full_classification = models.CharField(max_length=300, blank=True)

    # ACE institution size: "Large", "Medium", "Small", "Very Large", "Very Small"
    carnegie_size = models.CharField(max_length=50, blank=True)

    # ROR ID of parent institution (e.g. UC system is parent of UC Berkeley)
    parent_ror_id = models.CharField(max_length=100, blank=True)

    # Primary web domain for email-based matching, e.g. "uchicago.edu"
    website_domain = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class InstitutionAlias(models.Model):
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="aliases"
    )
    alias = models.CharField(max_length=500)


class UserInstitution(models.Model):
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="users"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="institutions",
    )


class KeycloakUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="keycloak_user"
    )
    sub = models.CharField(max_length=255, unique=True, null=True, blank=True)


class Reviewer(models.Model):
    class ReviewType(models.TextChoices):
        ALLOCATION = "allocation", "Allocation"
        PI_ELIGIBILITY = "pi_eligibility", "PI Eligibility"
        PUBLICATION = "publication", "Publication"

    review_type = models.CharField(
        max_length=50, choices=ReviewType.choices, unique=True
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
        related_name="+",
    )

    def __str__(self):
        return self.get_review_type_display()

    @classmethod
    def get_rt_owner(cls, review_type):
        try:
            obj = cls.objects.select_related("reviewer").get(review_type=review_type)
            return obj.reviewer.email if obj.reviewer else ""
        except cls.DoesNotExist:
            return ""


class Dataset(models.Model):
    name = models.CharField(max_length=1024, unique=True)
    url = models.CharField(max_length=1024)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class DatasetDownloadEvent(models.Model):
    downloaded_at = models.DateTimeField(auto_now_add=True)
    downloaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
    )
