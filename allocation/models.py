
import datetime

from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from django.db import models

from user.models import ChameleonUser

def _descriptionFileLocation(allocation_request, filename):
    (name, extension) = os.path.splitext(filename)
    return os.path.join(settings.MEDIA_ROOT,"allocation_requests",allocation_requests,"description."+extension)


# Alamo virtual machines, Hotel virtual machines
# Alamo object store?, Hotel object store?
# Alamo bare metal, Hotel bare metal
# etc.
class Resource(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

#class ScienceField(models.CharField):
#    FIELDS = (
#        ("",""),
#    )
#
#    def __init__(self, *args, **kwargs):
#        kwargs["max_length"] = 100
#        kwargs["choices"] = ScienceField.FIELDS
#        models.CharField.__init__(self,*args,**kwargs)

# this is an alternative to ScienceField
class FieldOfScience(models.Model):
    name = models.CharField(max_length=100)
    #parent = models.OneToOneField(FieldOfScience,blank=True)

    def __unicode__(self):
        return self.name

# FutureGrid project process:
#   * create an AllocationRequest for each one
#   * when the PI or allocation manager claims it, create the Group and Allocation

class AllocationRequest(models.Model):
    title = models.CharField(max_length=100,
                             blank=True,
                             help_text="a title is not needed if this request applies to an existing allocation")

    # name should either be unique or match an existing Allocation managed by the user
    # name should be a valid Linux group name
    #   at most 16 characters
    #   satisfying: [a-z][0-9a-z\-]*
    #   can't be an existing User name
    name = models.CharField(max_length=16,
                            help_text="a short project name (use the name of an existing allocation if you are modifying that allocation). [_a-z][_a-z-0-9]*",
                            validators=[RegexValidator('^[_a-z][_a-z-0-9]*$',
                                                       'Enter a valid allocation name.',
                                                       'invalid')])

    abstract = models.TextField(max_length=2000)
    key_words = models.CharField(max_length=200)

    # The PI for a New allocation, the PI or allocation manager for the others
    requester = models.OneToOneField(ChameleonUser,related_name="alloc_req_requester")

    initial_users = models.ManyToManyField(ChameleonUser,blank=True,related_name="alloc_req_initial_users")

    fields_of_science = models.ManyToManyField(FieldOfScience)
    #primary_field_of_science = ScienceField()
    #secondary_field_of_science = ScienceField(blank=True)

    # should grants be a separate Model?
    nsf_grant = models.CharField(max_length=50,
                                 blank=True,
                                 help_text="the NSF grant that will be supported by this allocation (optional)")

    project_url = models.URLField(blank=True,
                                  help_text="a URL for the project supported by this allocation (optional)")

    # alternative way that stores the fields in the database
    #field_of_science = models.ManyToManyField(FieldOfScience)

    # extension - more duration, no more units
    # supplement - more units, no more duration
    # renewal - more units and duration
    TYPE = (
        ("N","New"),
        ("E","Extension"),
        ("S","Supplement"),
        ("R","Renewal"),
    )
    request_type = models.CharField(max_length=1,choices=TYPE)

    # documents from XSEDE: main document, PI CV, Code performance and scaling
    description = models.FileField(upload_to=_descriptionFileLocation,
                                   blank=True,
                                   help_text="project description - required for large allocations")
    
    resources = models.ManyToManyField(Resource,help_text="the resources you expect to use")

    units = models.IntegerField(default=10000,
                                help_text="the number of units requested")
    duration = models.IntegerField(default=12,
                                   help_text="the number of months the allocation will be valid for")

    accept_allocation_agreement = models.BooleanField(default=False,
                                                      help_text="accept the Chameleon allocation agreement")

    # if editable=False, it isn't displayed in the admin interface
    # if editable=True, it is shown in the allocation request form
    submit_date = models.DateTimeField(default=datetime.datetime.now,editable=False)

    review_date = models.DateTimeField(default=datetime.datetime.now)

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

    def __unicode__(self):
        return self.title

class Allocation(models.Model):
    # name is validated in AllocationRequest
    name = models.CharField(max_length=16,unique=True,help_text="a short project name")

    # these need to be ManyToMany
    principal_investigator = models.OneToOneField(ChameleonUser,related_name="pi")
    allocation_manager = models.OneToOneField(ChameleonUser,null=True,blank=True,related_name="manager",
                                              help_text="an alternate user that can manage this allocation")
    users = models.ManyToManyField(ChameleonUser,blank=True,related_name="users")

    join_requests = models.ManyToManyField(ChameleonUser, help_text="users that have asked to join this allocation")

    # could be several requests associated with an allocation
    allocation_requests = models.ManyToManyField(AllocationRequest)

    start_date = models.DateField()
    end_date = models.DateField()

    granted_units = models.IntegerField(help_text="the amount of units granted")
    remaining_units = models.IntegerField(help_text="the amount of units remaining")

    summary_of_results = models.TextField(max_length=2000,blank=True)

    #publications

    def __unicode__(self):
        return self.name
