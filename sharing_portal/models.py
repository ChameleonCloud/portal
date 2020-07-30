import json
import re

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from sharing_portal.utils import get_zenodo_file_link
from sharing_portal.conf import JUPYTERHUB_URL, ZENODO_SANDBOX
from sharing_portal.zenodo import ZenodoClient


def validate_git_repo(repo):
    """Validator to make sure that the GitHub repo is in the right format

    Args:
        repo (str): GitHub repo reference to validate.

    Raises:
        ValidationError: if the Git repo reference is not of the form
            {user|org}/{repo}
    """
    if not re.match(r"[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+", str(repo)):
        raise ValidationError("This must be in the form {user|org}/{repo}")


def validate_zenodo_doi(doi):
    """Validator to make sure that the Zenodo DOI is in the right format

    Args:
        doi (str): the Zenodo DOI to validate.

    Raises:
        ValidationError: if the DOI is malformed
    """
    if not re.match(r'10\.[0-9]+\/zenodo\.[0-9]+$', str(doi)):
        raise ValidationError("Please enter a valid Zenodo DOI")


class Author(models.Model):
    """
    Represents authors of an artifact
    """
    affiliation = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=200)

    # Order by last name
    class Meta:
        ordering = ('name',)

    def __str__(self):
        display = self.name
        if self.affiliation:
            display += ' ({})'.format(self.affiliation)
        return display


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
    launch_count = models.IntegerField(default=0)

    """ Default Methods """
    # Order by title
    class Meta:
        ordering = ('title', )

    # Printing a record = printing its title
    def __str__(self):
        return self.title

    @property
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

    @property
    def versions(self):
        return self.artifact_versions.order_by('created_at')

    @property
    def related_items(self):
        """
        Find related artifacts based on labels

        FIXME: this method looks to use an expensive query to get all the related
        items from the database. It could likely be simplified into a more efficient
        query with some QuerySet wrangling. Could also not really be a problem
        depending on how it executes under the hood.
        """
        related_list = [
            artifact
            for label in self.labels.all()
            for artifact in label.artifacts.all()
            if artifact.id != self.id
        ]
        related_list = list(set(related_list))
        return related_list[:6]

    @property
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

    @property
    def search_terms(self):
        terms = self.title.lower().split()
        terms.extend([l.label.lower() for l in self.labels.all()])
        return terms


class ArtifactVersion(models.Model):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE, related_name='artifact_versions')
    created_at = models.DateTimeField()
    doi = models.CharField(max_length=50, blank=True,
                           validators=[validate_zenodo_doi])
    launch_count = models.IntegerField(default=0)

    @property
    def zenodo_link(self):
        if not self.doi:
            return None

        if ZENODO_SANDBOX:
            base_url = "https://sandbox.zenodo.org"
        else:
            base_url = "https://zenodo.org"

        return '{}/record/{}'.format(base_url, ZenodoClient.to_record(self.doi))
