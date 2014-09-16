from django.db import models

class System(models.Model):
    name = models.CharField(max_length=100,primary_key=True,unique=True)
    location = models.CharField(max_length=100)
    description = models.CharField(max_length=2000)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)
