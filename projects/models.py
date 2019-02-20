from django.db import models

class ProjectExtras(models.Model):
    project_id = models.IntegerField(primary_key=True)
    nickname = models.CharField(max_length=50,blank=True,null=True)
