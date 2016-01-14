from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

class Keyword(models.Model):
	name = models.CharField(max_length=50, primary_key=True)
	def __unicode__(self):
		return self.name

class Appliance(models.Model):
	name = models.CharField(max_length=50)
	description = models.TextField(max_length=5000)
	appliance_icon = models.ImageField(upload_to='appliance_catalog/icons/', default='appliance_catalog/icons/default.png', blank=True)
	chi_tacc_appliance_id = models.IntegerField(null=True, blank=True)
	chi_uc_appliance_id = models.IntegerField(null=True, blank=True)
	kvm_tacc_appliance_id = models.IntegerField(null=True, blank=True)
	author_name = models.CharField(max_length=50)
	author_url = models.CharField(max_length=500)
	support_contact_name = models.CharField(max_length=50)
	support_contact_url = models.CharField(max_length=500)
	project_supported = models.BooleanField(default=False, blank=True)
	keywords = models.ManyToManyField(Keyword, through='ApplianceTagging', null=True, blank=True)
	version = models.CharField(max_length=50)
	created_user = models.CharField(max_length=50, editable=False)
	updated_user = models.CharField(max_length=50, editable=False, null=True)
	created_date = models.DateTimeField(auto_now_add=True)
	updated_date = models.DateTimeField(auto_now=True)

	def __unicode__(self):
		return self.name

class ApplianceTagging(models.Model):
	keyword = models.ForeignKey(Keyword)
	appliance = models.ForeignKey(Appliance)
