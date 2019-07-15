import os

from django.db import models
from django.core.exceptions import ValidationError

class Author(models.Model):
    title = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=600,editable=False)

    class Meta:
        ordering = ('last_name',)
    def __str__(self):
        return self.title+" "+self.first_name+" "+self.last_name

    def save(self):
        self.full_name = self.title+" "+self.first_name+" "+self.last_name
        super(Author, self).save()

class LabelField(models.CharField):
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
    short_description = models.CharField(max_length=70)
    description = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='sharing/static/sharing/images/',blank=True,null=True)

    def image_filename(self):
        if self.image is not None:
            ilist = self.image.url.split('/')
            return ilist[len(ilist)-1]
        else:
            return None

    def validate_git_repo(value):
        error = "This must be in the form user_or_organization/repo_name"
        parts = value.split("/")
        if (len(parts) != 2):
            raise ValidationError(error)
        if (' ' in parts[0]) or (' ' in parts[1]):
            raise ValidationError(error)
    def validate_zenodo_doi(value):
        error = "Please enter a valid Zenodo DOI"
        parts = value.split("/")
        if (len(parts) != 2):
            raise ValidationError(error)
        if ' ' in value:
            raise ValidationError(error)
        zparts = parts[1].split('.')
        if (len(zparts) != 2):
            raise ValidationError(error)
        if zparts[0] != "zenodo":
            raise ValidationError(error)
        if not zparts[1].isnumeric():
            raise ValidationError(error)

    doi = models.CharField(max_length=50, blank=True, null=True,
        validators=[validate_zenodo_doi])
    git_repo = models.CharField(max_length=200, blank=True,
        null=True,validators=[validate_git_repo])

    launchable = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    labels = models.ManyToManyField(Label, related_name='artifacts', blank=True)
    associated_artifacts = models.ManyToManyField("Artifact", related_name='associated', blank=True)

    class Meta:
        ordering = ('title',)

    def zenodo_link(self):
        zparts = self.doi.split('.')
        return "https://zenodo.org/record/"+zparts[len(zparts)-1]

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
# - ForeignKeyList artifacts

