import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
import django_countries
from django_countries.fields import CountryField

def _profileImageLocation(person, filename):
    (name, extension) = os.path.splitext(filename)
    return os.path.join(settings.MEDIA_ROOT,"people",person.user.get_username(),"picture."+extension)

def _profileCVLocation(person, filename):
    (name, extension) = os.path.splitext(filename)
    return os.path.join(settings.MEDIA_ROOT,"people",person.user.get_username(),"cv."+extension)

class Institution(models.Model):
    name = models.CharField(max_length=100,
                            help_text="name of university, company, or other institution")
    address1 = models.CharField(max_length=100)
    address2 = models.CharField(max_length=100)
    address3 = models.CharField(max_length=100)
    # would be nice to have a drop down of countries, then the states in that country
    #   maybe django-localflavor could help
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=100)
    country = CountryField()

    def __unicode__(self):
        return name

# We have Groups - don't need this?
class ChameleonRole(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Person(models.Model):
    user = models.OneToOneField(User)
    image = models.ImageField(upload_to=_profileImageLocation,
                              blank=True,
                              help_text="Profile Picture")
    institution = models.OneToOneField(Institution)
    #institutions = models.ManyToManyField(Institution,through='InstitutionMembership')
    department = models.CharField(max_length=100,
                                  help_text="department or division")

    home_page = models.URLField(blank=True,
                                help_text="a personal home page")

    bio = models.TextField(max_length=2000,
                           blank=True,
                           help_text="a short biography")

    cv = models.FileField(upload_to=_profileCVLocation,
                          blank=True,
                          help_text="Curriculum vitae")

    # futuregrid has separate Phd and Master's students
    # need a post doc role?
    ROLE = (
        ("US","Undergraduate Student"),
        ("GS","Graduate Student"),
        ("Fa","Faculty"),
        ("St","Staff"),
        ("Ot","Other"),
    )
    institution_role = models.CharField(max_length=2,choices=ROLE)

    citizenship = CountryField()

    request_PI = models.BooleanField(default=False,
                                    help_text="request to be able to request allocations")
    accepted_AUP = models.BooleanField(default=False,
                                      help_text="agreed to the Chameleon aceptable usage policy")
    roles = models.ManyToManyField(ChameleonRole)


    def __unicode__(self):
        return "%s %s" % (self.user.first_name,self.user.last_name)
