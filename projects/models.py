from django.db import models

class ProjectExtras(models.Model):
    tas_project_id = models.IntegerField(primary_key=True)
    charge_code = models.CharField(max_length=50,blank=False,null=False)
    nickname = models.CharField(max_length=50,blank=True,null=True)
