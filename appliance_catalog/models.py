from django.db import models

class Keyword(models.Model):
	name = models.CharField(max_length=50)
	def __unicode__(self):
		return self.name

class Appliance(models.Model):
	name = models.CharField(max_length=50)
	description = models.TextField(max_length=5000)
	appliance_icon = models.ImageField(upload_to = 'appliance_catalog/icons/', default = 'appliance_catalog/icons/default.png')
	chi_tacc_appliance_id = models.IntegerField(null=True)
	chi_uc_appliance_id = models.IntegerField(null=True)
	kvm_tacc_appliance_id = models.IntegerField(null=True)
	author_name = models.CharField(max_length=50)
	author_url = models.CharField(max_length=500)
	support_contact_name = models.CharField(max_length=50)
	support_contact_url = models.CharField(max_length=500)
	project_supported = models.BooleanField(default=False)
	keywords = models.ManyToManyField(Keyword)
	version = models.CharField(max_length=50)
	created_user = models.CharField(max_length=50, editable=False)
	updated_user = models.CharField(max_length=50, editable=False, null=True)
	created_date = models.DateTimeField(auto_now_add=True)
	updated_date = models.DateTimeField(auto_now=True)

	def __unicode__(self):
		return self.name