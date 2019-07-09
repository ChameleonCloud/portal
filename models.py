import datetime
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import requests

class Author(models.Model):
    title = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)

    class Meta:
        ordering = ('last_name',)
    def __str__(self):
        return self.title+" "+self.first_name+" "+self.last_name

class LabelField(models.CharField):
    def to_python(self, value):
        return value.lower()
'''
    def __init__(self, *args, **kwargs):
        super(SnpField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        return str(value).lower()

'''
class Label(models.Model):
    label = LabelField(max_length=50)
    class Meta:
        ordering = ('label',)
    def __str__(self):
        return self.label

class Artifact(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name='artifacts')
    short_description = models.CharField(max_length=70)
    description = models.TextField(max_length=5000)
    image = models.CharField(max_length=100)

    def validate_git_repo(value):
        error = "This must be in the form user_or_organization/repo_name"
        parts = value.split("/")
        if (len(parts) != 2):
            raise ValidationError(error)
        if (' ' in parts[0]) or (' ' in parts[1]):
            raise ValidationError(error)
    def validate_doi(value):
        error = "Please enter a valid DOI"
        if ' ' in value:
            raise ValidationError(error)

    DOI = models.CharField(max_length=50, blank=True, null=True,
        validators=[validate_doi])
    git_repo = models.CharField(max_length=200, blank=True,
        null=True,validators=[validate_git_repo])

    launchable = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    labels = models.ManyToManyField(Label, related_name='artifacts', blank=True)

    class Meta:
        ordering = ('title',)
    
    def src(self):
        if self.git_repo is not None:
            return "git"
        elif self.DOI is not None:
            return "zenodo"
        else:
            return "none"

    def src_path(self):
        src = self.src()
        if (src == "git"):
            return self.git_repo+".git"
        elif src == "zenodo":
            return Exception("currently not working for zenodo")
            # Currently not working
        else:
            raise Exception("Asked to get source path with no provided source")

    def jupyterhub_link(self):
        base_url = "http://localhost:8000/hub/import/exp_name?imported=yes"
         #TODO: change to real url for deployment
        link = base_url + "&source=" + self.src() + "&src_path=" + self.src_path()
        return link

    def related_papers(self):
        related_list = [artifact 
            for label in self.labels.all()
            for artifact in label.artifacts.all()
            if artifact.id != self.id
            ]
        return related_list[:6]
            
    def __str__(self):
        return self.title

## Making Changes ##
# 1. Change your models (in models.py).
# 2. Run python manage.py makemigrations to create migrations for those changes
# 3. Run python manage.py migrate to apply those changes to the database.
 

## ARTIFACTS ##
# - id
# - string title
# - string descritipn
# - string image
# - string DOI
# - string git_repo
# - bool launchable
# - datetime created_at
# - datetime updated_at
# - bool deleted
# - datetime deleted_at
# - ForeignKey author

## AUTHORS ##
# - string name
# ForeignKeyList artifacts

# Create your models here.
