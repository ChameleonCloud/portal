from django.db import models


class Keyword(models.Model):
    name = models.CharField(max_length=50, primary_key=True)


    def __unicode__(self):
        return self.name


class Appliance(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=5000)
    appliance_icon = models.ImageField(upload_to='appliance_catalog/icons/', blank=True)
    chi_tacc_appliance_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    chi_uc_appliance_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    kvm_tacc_appliance_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    author_name = models.CharField(max_length=1000)
    author_url = models.CharField(max_length=500)
    support_contact_name = models.CharField(max_length=100)
    support_contact_url = models.CharField(max_length=500)
    project_supported = models.BooleanField(default=False, blank=True)
    project_flagged = models.BooleanField(default=False, blank=True)
    keywords = models.ManyToManyField(Keyword, through='ApplianceTagging', null=True, blank=True)
    version = models.CharField(max_length=100)
    created_user = models.CharField(max_length=100, editable=False)
    updated_user = models.CharField(max_length=100, editable=False, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


    def __unicode__(self):
        return self.name


class ApplianceTagging(models.Model):
    keyword = models.ForeignKey(Keyword)
    appliance = models.ForeignKey(Appliance)
