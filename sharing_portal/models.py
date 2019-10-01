import json
import re
from urllib.request import urlopen, Request

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
    
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from sharing_portal.utils import get_rec_id, get_zenodo_file_link, get_permanent_id
from sharing_portal.conf import JUPYTERHUB_URL, ZENODO_SANDBOX


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

    if not re.match(r"[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+", str(repo)):
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
    if not re.match(r'10\.[0-9]+\/zenodo\.[0-9]+$', str(doi)):
        raise ValidationError(error)


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
        return self.full_name

    # Save the full name along with all the pieces for search purposes
    def save(self, *args, **kwargs):
        self.full_name = self.title+" "+self.first_name+" "+self.last_name
        super(Author, self).save(*args, **kwargs)


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
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name='artifacts')
    short_description = models.CharField(max_length=70, blank=True, null=True)
    description = models.TextField(max_length=5000)
    image = models.ImageField(upload_to='sharing_portal/images/',
                              blank=True, null=True)
    doi = models.CharField(max_length=50, blank=True, null=True,
                           validators=[validate_zenodo_doi])
    permanent_id = models.CharField(max_length=50, editable=False,
                                    blank=True, default='')
    git_repo = models.CharField(max_length=200, blank=True,
                                null=True, validators=[validate_git_repo])
    launchable = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='artifacts',
                                   null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    labels = models.ManyToManyField(Label, related_name='artifacts',
                                    blank=True)
    associated_artifacts = models.ManyToManyField("Artifact",
                                                  related_name='associated',
                                                  blank=True)

    """ Default Methods """
    # Order by title
    class Meta:
        ordering = ('title', )

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
        - Uses self.doi
        """

        if ZENODO_SANDBOX:
            base_url = "https://sandbox.zenodo.org/record/"
        else:
            base_url = "https://zenodo.org/record/"

        if not self.permanent_id:
            self.permanent_id = get_permanent_id(self.doi)

        return base_url + self.permanent_id

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
        - Uses self.git_repo or self.doi
        """
        base_url = JUPYTERHUB_URL + '/hub/import'

        if self.git_repo:
            query = dict(
                source='github',
                src_path=self.git_repo,
            )
        elif self.doi:
            query = dict(
                source=('zenodo_sandbox' if ZENODO_SANDBOX else 'zenodo'),
                src_path=self.doi,
            )
        else:
            raise Exception("Non-launchable artifact has no JupyterHub link")

        # Add query parameters before returning
        return base_url + '?' + urlencode(query)

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