import json
import os
import re
from urllib.request import urlopen, Request

from django.db import models
from django.core.exceptions import ValidationError


#TODO: set this dynamically
dev = True

def get_rec_id(doi):
    """ Extract the deposition ID from a DOI
    Parameters
    ----------
    doi : string
        DOI to extract from
    
    Returns
    -------
    string
        Extracted ID

    Notes
    -----
    - No error handling
    - DOIs are in the form xxxxx/zenodo.xxxxx
    """

    return doi.split('.')[-1]

def get_zenodo_file(record_id):
    """ Get filename from deposition
    Parameters
    ----------
    record_id : string
        ID of deposition to get file from
    
    Returns
    -------
    string
        Retrieved file name 

    Notes
    -----
    - No error handling
    """
 
    # Use Zenodo sandbox while in development
    if dev:
        api = "https://sandbox.zenodo.org/api/records/"
    else:
        api = "https://zenodo.org/api/records/"

    # Send a request to the Zenodo API
    req = Request(
        "{}{}".format(api, record_id),
        headers={"accept": "application/json"},
    )
    resp = urlopen(req)
    record = json.loads(resp.read().decode("utf-8"))

    # Return the first file's name
    return record['files'][0]['filename']

class Author(models.Model):
    title = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=600,editable=False)

    # Order by last name
    class Meta:
        ordering = ('last_name',)

    # Print the author's full name when printing
    def __str__(self):
        return self.title+" "+self.first_name+" "+self.last_name

    # Save the full name along with all the pieces for search purposes
    def save(self):
        self.full_name = self.title+" "+self.first_name+" "+self.last_name
        super(Author, self).save()

class LabelField(models.CharField):
    """ Custom field that is always lowercase """
    def to_python(self, value):
        return value.lower()

class Label(models.Model):
    label = LabelField(max_length=50)
    class Meta:
        ordering = ('label',)
    def __str__(self):
        return self.label

class Artifact(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name='artifacts')
    short_description = models.CharField(max_length=70, blank=True, null=True)
    description = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='sharing/static/sharing/images/',blank=True,null=True)

    def image_filename(self):
        if self.image is not None:
            ilist = self.image.url.split('/')
            return ilist[len(ilist)-1]
        else:
            return None

    def validate_git_repo(repo):
        """ Validator to make sure that the git repo is in the right format

        Parameters
        ----------
        repo : string
            Git repo to validate 

        Returns
        -------
        void
        """
        error = "This must be in the form user_or_organization/repo_name"
        
        if not re.match("[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+", repo):
            raise ValidationError(error)
        """
        parts = repo.split("/")
        if (len(parts) != 2):
            raise ValidationError(error)
        if (' ' in parts[0]) or (' ' in parts[1]):
            raise ValidationError(error)
        """

    def validate_zenodo_doi(doi):
        """ Validator to make sure that the Zenodo DOI is in the right format

        Parameters
        ----------
        doi : string
            Zenodo doi to validate 

        Returns
        -------
        void
        """
 
        error = "Please enter a valid Zenodo DOI"
        if not re.match("10\.[0-9]+\/zenodo\.[0-9]+$", doi):
            raise ValidationError(error)

    doi = models.CharField(max_length=50, blank=True, null=True,
        validators=[validate_zenodo_doi])
    #zenodo_id = models.CharField(max_length=50,editable=False, blank=True, null=True, default='')
    git_repo = models.CharField(max_length=200, blank=True,
        null=True,validators=[validate_git_repo])

    launchable = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    labels = models.ManyToManyField(Label, related_name='artifacts', blank=True)
    associated_artifacts = models.ManyToManyField("Artifact", related_name='associated', blank=True)

    # Order by title
    class Meta:
        ordering = ('title',)

    def zenodo_link(self):
        # Zenodo link is based on the record ID
        if dev:
            base_url = "https://sandbox.zenodo.org/record/"
        else: 
            base_url = "https://zenodo.org/record/"

        if not self.zenodo_id:
            self.zenodo_id = get_rec_id(self.doi)
        return base_url + self.zenodo_id

    def src(self):
        if self.git_repo:
            return "git"
        elif self.doi:
            return "zenodo"
        else:
            return "none"

    def src_path(self):
        src = self.src()
        if (src == "git"):
            return self.git_repo+".git"
        elif src == "zenodo":
            self.zenodo_id = get_rec_id(self.doi)
            record_id = self.zenodo_id
            filename = get_zenodo_file(record_id)
            zen_path = "record/"+record_id+"/files/"+filename
            return zen_path
        else:
            raise Exception("Asked to get source path with no provided source")

    def jupyterhub_link(self):
        if dev:
            hub_url = "http://localhost:8000" 
        else:
            hub_url = "https://jupyter.chameleoncloud.org"
        import_indicator = "/hub/import/exp_name?imported=yes"
        base_url = hub_url + import_indicator
        link = base_url + "&source=" + self.src() + "&src_path=" + self.src_path()
        return link

    def related_papers(self):
        related_list = [artifact 
            for label in self.labels.all()
            for artifact in label.artifacts.all()
            if artifact.id != self.id
            ]
        related_list = list(set(related_list))
        return related_list[:6]
            
    # On save, store Zenodo record ID if applicable
    def save(self):
        if self.doi:
            self.zenodo_id = get_rec_id(self.doi)
        super(Artifact, self).save()

    # Printing a record = printing its title
    def __str__(self):
        return self.title

## Making Changes ##
# 1. Change your models (in models.py).
# 2. Run python manage.py makemigrations to create migrations for those changes
# 3. Run python manage.py migrate to apply those changes to the database.
