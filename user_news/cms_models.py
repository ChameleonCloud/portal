from django.db import models
from cms.models.pluginmodel import CMSPlugin

class UserNewsPluginModel(CMSPlugin):
    limit = models.IntegerField(default=5)
