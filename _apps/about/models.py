from django.db import models

class TeamRole(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class TeamMember(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    image = models.CharField(max_length=200)
    organization = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    roles = models.ManyToManyField(TeamRole)

    def __unicode__(self):
        return "%s %s" % (self.first_name,self.last_name)
