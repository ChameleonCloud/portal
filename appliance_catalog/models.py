from django.conf import settings
from django.db import models


class Keyword(models.Model):
    name = models.CharField(max_length=50, primary_key=True)

    def __str__(self):
        return self.name


class Appliance(models.Model):
    name = models.CharField(max_length=100)
    short_description = models.CharField(max_length=140)
    description = models.TextField()
    documentation = models.TextField(null=True, blank=True)
    appliance_icon = models.ImageField(upload_to="appliance_catalog/icons/", blank=True)
    chi_tacc_appliance_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )
    chi_uc_appliance_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )
    kvm_tacc_appliance_id = models.CharField(
        max_length=100, null=True, blank=True, unique=True
    )
    template = models.TextField(null=True, blank=True)
    author_name = models.CharField(max_length=1000)
    author_url = models.CharField(max_length=500)
    support_contact_name = models.CharField(max_length=100)
    support_contact_url = models.CharField(max_length=500)
    project_supported = models.BooleanField(default=False, blank=True)
    # Indicates if appliance was shared directly from an image in Horizon
    shared_from_horizon = models.BooleanField(default=False)
    # Indicates which projects (if any) the appliance is shared with, an empty list indicates a public appliance
    restrict_to_projects = models.CharField(max_length=1000, null=True, blank=True)
    project_flagged = models.BooleanField(default=False, blank=True)
    keywords = models.ManyToManyField(Keyword, through="ApplianceTagging", blank=True)
    version = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="appliances", on_delete=models.CASCADE
    )
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    needs_review = models.BooleanField(default=True, blank=True)

    def __str__(self):
        return self.name


class ApplianceTagging(models.Model):
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE)
    appliance = models.ForeignKey(Appliance, on_delete=models.CASCADE)
