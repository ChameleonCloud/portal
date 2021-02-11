import json
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from projects.models import Project
from sharing_portal.zenodo import ZenodoClient

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib.parse import urlencode


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
    if not re.match(r"10\.[0-9]+\/zenodo\.[0-9]+$", str(doi)):
        raise ValidationError("Please enter a valid Zenodo DOI")


def gen_sharing_key():
    return uuid.uuid4().hex


class Author(models.Model):
    """
    Represents authors of an artifact
    """

    affiliation = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=200)

    # Order by last name
    class Meta:
        ordering = ("name",)

    def __str__(self):
        display = self.name
        if self.affiliation:
            display += " ({})".format(self.affiliation)
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
        ordering = ("label",)

    def __str__(self):
        return self.label


class Artifact(models.Model):
    """
    Represents artifacts
    These could be research projects, Zenodo depositions, etc
    """

    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name="artifacts")
    short_description = models.CharField(max_length=70, blank=True, null=True)
    description = models.TextField(max_length=5000)
    doi = models.CharField(
        max_length=50, blank=True, null=True, validators=[validate_zenodo_doi]
    )
    git_repo = models.CharField(
        max_length=200, blank=True, null=True, validators=[validate_git_repo]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="artifacts",
        null=True,
        on_delete=models.CASCADE,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
    )
    sharing_key = models.CharField(max_length=32, null=True, default=gen_sharing_key)
    labels = models.ManyToManyField(Label, related_name="artifacts", blank=True)
    associated_artifacts = models.ManyToManyField(
        "Artifact", related_name="associated", blank=True
    )
    shared_to_projects = models.ManyToManyField(Project, through="ShareTarget")

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title

    @property
    def versions(self):
        return self.artifact_versions.order_by("created_at")

    @property
    def related_items(self):
        """Find related artifacts based on labels.

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
    def search_terms(self):
        terms = self.title.lower().split()
        terms.extend([l.label.lower() for l in self.labels.all()])
        return terms

    @property
    def launch_count(self):
        return sum([v.launch_count for v in self.versions.all()])

    @property
    def deposition_url(self):
        return ZenodoClient.to_record_url(self.doi) if self.doi else None


class ArtifactVersion(models.Model):
    ZENODO = "zenodo"
    CHAMELEON = "chameleon"
    GIT = "git"
    DEPOSITION_REPO_CHOICES = (
        (ZENODO, "Zenodo"),
        (CHAMELEON, "Chameleon"),
        (GIT, "Git"),
    )

    artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="artifact_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deposition_id = models.CharField(max_length=50)
    deposition_repo = models.CharField(
        max_length=24, choices=DEPOSITION_REPO_CHOICES, default=CHAMELEON
    )
    launch_count = models.IntegerField(default=0)

    def clean(self):
        if self.deposition_repo == self.ZENODO:
            validate_zenodo_doi(self.deposition_id)
        elif self.deposition_repo == self.GIT:
            validate_git_repo(self.deposition_id)

    @property
    def doi(self):
        if self.deposition_repo == self.ZENODO:
            return self.deposition_id
        else:
            return None

    @property
    def deposition_url(self):
        if self.deposition_repo == self.ZENODO:
            return ZenodoClient.to_record_url(self.doi)
        else:
            return None

    def launch_url(self, can_edit=False):
        base_url = "{}/hub/import".format(settings.ARTIFACT_SHARING_JUPYTERHUB_URL)
        query = dict(
            deposition_repo=self.deposition_repo,
            deposition_id=self.deposition_id,
            id=self.artifact.id,
            ownership=("own" if can_edit else "fork"),
        )
        return str(base_url + "?" + urlencode(query))

    def __str__(self):
        return f"{self.artifact.title} ({self.created_at})"


class ShareTarget(models.Model):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
