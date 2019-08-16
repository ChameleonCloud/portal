import json
import re
from urllib.request import urlopen, Request

from django.core.exceptions import ValidationError
from django.db import models

from .__init__ import DEV as dev
from .utils import get_rec_id, get_zenodo_file


class Author(models.Model):
    """
    Represents authors of an artifact
    """
    title = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=600, editable=False)

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
    """
    Represents artifact tags
    """
    label = LabelField(max_length=50)

    class Meta:
        ordering = ('label',)

    def __str__(self):
        return self.label


class Artifact(models.Model):
    """
    Represents artifacts
    These could be research projects, Zenodo depositions, etc
    """

    """ Validators """
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

        if not re.match(r'[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+', repo):
            raise ValidationError(error)

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
        if not re.match(r'10\.[0-9]+\/zenodo\.[0-9]+$', doi):
            raise ValidationError(error)

    """ Fields """
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name='artifacts')
    short_description = models.CharField(max_length=70, blank=True, null=True)
    description = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='sharing/static/sharing/images/',
                              blank=True, null=True)
    doi = models.CharField(max_length=50, blank=True, null=True,
                           validators=[validate_zenodo_doi])
    zenodo_id = models.CharField(max_length=50, editable=False,
                                 blank=True, default='')
    git_repo = models.CharField(max_length=200, blank=True,
                                null=True, validators=[validate_git_repo])
    launchable = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    labels = models.ManyToManyField(Label, related_name='artifacts',
                                    blank=True)
    associated_artifacts = models.ManyToManyField("Artifact",
                                                  related_name='associated',
                                                  blank=True)

    """ Default Methods """
    # Order by title
    class Meta:
        ordering = ('title', )

    # On save, store Zenodo record ID if applicable
    def save(self):
        if self.doi:
            self.zenodo_id = get_rec_id(self.doi)
        super(Artifact, self).save()

    # Printing a record = printing its title
    def __str__(self):
        return self.title

    """ Custom Methods """
    def zenodo_link(self):
        """ Method to build a link to view an artifact on Zenodo

        Parameters
        ----------
        none

        Returns
        -------
        string
            Zenodo URL

        Notes
        -----
        - Uses self.doi and self.zenodo_id
        """

        # Use sandbox if in dev mode
        if dev:
            base_url = "https://sandbox.zenodo.org/record/"
        else:
            base_url = "https://zenodo.org/record/"

        if not self.zenodo_id:
            self.zenodo_id = get_rec_id(self.doi)
        return base_url + self.zenodo_id

    def jupyterhub_link(self):
        """ Method to build a link to open the artifact files on JupyterHub

        Parameters
        ----------
        none

        Returns
        -------
        string
            Zenodo URL

        Notes
        -----
        - Uses self.git_repo or self.doi and self.zenodo_id
        """
        # Hub url is different in development
        if dev:
            hub_url = "http://localhost:8000"
        else:
            hub_url = "https://jupyter.chameleoncloud.org"
        import_indicator = "/hub/import?"

        # Add import indicator
        base_url = hub_url + import_indicator

        if self.git_repo:
            # Source path is just the git repo
            src_args = "source=git&src_path=" + self.git_repo + ".git"
        elif self.doi:
            # Build source path based on the record's files
            self.zenodo_id = get_rec_id(self.doi)
            filename = get_zenodo_file(self.zenodo_id)
            zen_path = "record/"+self.zenodo_id+"/files/"+filename
            src_args = "source=zenodo&src_path="+zen_path
        else:
            raise Exception("Non-launchable artifact has no JupyterHub link")
            
        # Add query parameters before returning
        return base_url + src_args

    def related_papers(self):
        """ Method to find related artifacts based on labels

        Parameters
        ----------
        none

        Returns
        -------
        list of artifacts
            6 artifacts with the same labels

        Notes
        -----
        - Uses self.labels.all()
        """
        related_list = [
            artifact
            for label in self.labels.all()
            for artifact in label.artifacts.all()
            if artifact.id != self.id
        ]
        related_list = list(set(related_list))
        return related_list[:6]

    def image_filename(self):
        """ Method to extract the filename from an image path

        Parameters
        ----------
        none

        Returns
        -------
        string or None
            image file name if it exists 

        Notes
        -----
        - Uses self.image
        """
 
        if self.image:
            return self.image.url.split('/')[-1]
        else:
            return None
