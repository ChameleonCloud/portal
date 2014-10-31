import ldap
import os

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AbstractUser, UserManager
from django.db import models
from django_countries.fields import CountryField

from django.contrib import auth

from backend import LDAPBackend

class LdapCheckUserMixIn(object):
    # AbstractBaseUser.check_password checks against the stored, hashes password
    #   but django_auth_ldap sets that to be set_unusable_password()
    # So, this version checks against ldap
    def check_password(self, password):
        #print("#### LdapCheckUserMixIn.check_password ####")
        try:
            self.ldap_user._authenticate_user_dn(password)
        except:
            return False
        return True

    # override to set the password in LDAP
    def set_password(self, password):
        print("#### LdapCheckUserMixIn.set_password ####")

        # password_reset calls UserModel._default_manager.get(filters)
        #   this pulls information directly from the Django database without a chance to intercept
        #   (e.g. in ChameleonUserManager)
        try:
            conn = self.ldap_user._get_connection()
            user_dn = self.ldap_user._get_user_dn()
        except AttributeError:
            uri = settings.AUTH_LDAP_SERVER_URI
            if callable(uri):
                uri = uri()
            conn = ldap.initialize(uri)

            template = settings.AUTH_LDAP_USER_DN_TEMPLATE
            username = ldap.dn.escape_dn_chars(self.username)
            user_dn = template % {'user': username}

        # don't have the current password for the user here, so need to connect as the portal
        conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

        conn.passwd_s(user_dn,None,password)

        conn.unbind_s()

class ChameleonUserManager(UserManager):
    pass

class ChameleonUser(LdapCheckUserMixIn, AbstractUser):
    objects = ChameleonUserManager()
    _default_manager = ChameleonUserManager()

    accepted_AUP = models.BooleanField(default=False,
                                      help_text="whether this user has accepted the Chameleon acceptable usage policy")

    is_PI = models.BooleanField(default=False,
                                help_text="whether this user can request allocations")


#class Institution(models.Model):
#    name = models.CharField(max_length=100,
#                            help_text="name of university, company, or other institution")
#    address1 = models.CharField(max_length=100)
#    address2 = models.CharField(max_length=100)
#    address3 = models.CharField(max_length=100)
    # would be nice to have a drop down of countries, then the states in that country
    #   maybe django-localflavor could help
#    city = models.CharField(max_length=100)
#    state = models.CharField(max_length=100)
#    postal_code = models.CharField(max_length=100)
#    country = CountryField(default="US")

#    def __unicode__(self):
#        return name

# used for the Team page
# We have Groups - don't need this?
class ChameleonRole(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

# these will come from and go to LDAP
class SshPublicKey(models.Model):
    user = models.OneToOneField(ChameleonUser)
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=1000)

    def __unicode__(self):
        return self.name

def _profileImageLocation(profile, filename):
    (name, extension) = os.path.splitext(filename)
    return os.path.join(settings.MEDIA_ROOT,"people",profile.user.get_username(),"picture."+extension)

def _profileCVLocation(profile, filename):
    (name, extension) = os.path.splitext(filename)
    return os.path.join(settings.MEDIA_ROOT,"people",profile.user.get_username(),"cv."+extension)

class UserProfile(models.Model):
    # should restrict username more: '^[a-z_][a-z0-9_]*$'
    # User.is_active for whether a user account has been approved
    user = models.OneToOneField(ChameleonUser)

    request_PI = models.BooleanField(default=False,
                                     help_text="whether you want to be able to request allocations")

    # a separate model is annoying for now
    #institution = models.OneToOneField(Institution)
    #institutions = models.ManyToManyField(Institution,through='InstitutionMembership')

    department = models.CharField(max_length=100,
                                  help_text="department or division (optional)")
    institution = models.CharField(max_length=100,
                                   help_text="name of university, company, or other institution")
    address1 = models.CharField(max_length=100,blank=True)
    address2 = models.CharField(max_length=100,blank=True)
    address3 = models.CharField(max_length=100,blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=100)
    country = CountryField(default="US")

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

    citizenship = CountryField(default="US")

    home_page = models.URLField(blank=True,
                                help_text="a personal home page (optional)")

    biography = models.TextField(max_length=2000,
                                 blank=True,
                                 help_text="a short biography (optional)")

    curriculum_vitae = models.FileField(upload_to=_profileCVLocation,
                                         blank=True,
                                         help_text="a CV (required for large allocation requests)")

    image = models.ImageField(upload_to=_profileImageLocation,
                              blank=True,
                              help_text="Profile Picture (optional)")
    STATUS = (
        ("I","Incomplete"),
        ("S","Submitted"),
        ("A","Approved"),
        ("D","Denied"),
    )
    status = models.CharField(max_length=1,choices=STATUS,default="I")

    deny_reason = models.TextField(max_length=2000,
                                   blank=True,
                                   help_text="the reason why an account request was denied (optional)")

    roles = models.ManyToManyField(ChameleonRole)

    def __unicode__(self):
        return "%s %s" % (self.user.first_name,self.user.last_name)
