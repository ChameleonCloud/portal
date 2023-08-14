import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from projects.models import Project, Invitation
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
    """Custom field that is always lowercase"""

    def to_python(self, value):
        return value.lower()


class Label(models.Model):
    """
    Represents artifact tags
    """

    label = LabelField(max_length=50)

    class Meta:
        ordering = ("label",)

    CHAMELEON_SUPPORTED = "chameleon"

    def __str__(self):
        return self.label


class Badge(models.Model):
    """
    Holds all the badges and their details
    """

    BADGE_REPRODUCIBLE_IN_TROVI = "reproducible"
    BADGE_SUPPORTED_BY_CHAMELEON = "chameleon"
    BADGE = (
        (BADGE_REPRODUCIBLE_IN_TROVI, "reproducible"),
        (BADGE_SUPPORTED_BY_CHAMELEON, "chameleon"),
    )
    name = models.CharField(max_length=50, blank=False, choices=BADGE)
    description = models.CharField(max_length=300, blank=False)
    redirect_link = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class ArtifactBadge(models.Model):
    """
    Represents artifact badges
    """

    artifact_uuid = models.CharField(max_length=36, null=True)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    STATUS_PENDING = "pending"
    STATUS_REJECTED = "rejected"
    STATUS_APPROVED = "approved"
    STATUS_DELETED = "deleted"
    STATUS = (
        (STATUS_PENDING, "pending"),
        (STATUS_REJECTED, "rejected"),
        (STATUS_APPROVED, "approved"),
        (STATUS_DELETED, "deleted"),
    )
    status = models.CharField(max_length=50, blank=False, choices=STATUS)
    requested_on = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    decision_at = models.DateTimeField(null=True)
    decision_summary = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)


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
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    sharing_key = models.CharField(max_length=32, null=True, default=gen_sharing_key)
    is_public = models.BooleanField(default=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="belongs_to_project", null=True
    )
    reproducibility_project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="reproducibility_project",
        null=True,
    )
    is_reproducible = models.BooleanField(default=False)
    reproduce_hours = models.IntegerField(null=True)
    labels = models.ManyToManyField(Label, related_name="artifacts", blank=True)
    associated_artifacts = models.ManyToManyField(
        "Artifact", related_name="associated", blank=True
    )
    shared_to_projects = models.ManyToManyField(Project, through="ShareTarget")
    trovi_uuid = models.CharField(max_length=36, null=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title

    @property
    def versions(self) -> "models.QuerySet[ArtifactVersion]":
        return self.artifact_versions.order_by("created_at")

    @property
    def related_items(self) -> "list[Artifact]":
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
    def search_terms(self) -> "list[str]":
        terms = self.title.lower().split()
        terms.extend([f"tag:{l.label.lower()}" for l in self.labels.all()])
        return terms

    @property
    def launch_count(self) -> "int":
        return sum([v.launch_count for v in self.versions.all()])

    @property
    def deposition_url(self) -> "str":
        return ZenodoClient.to_record_url(self.doi) if self.doi else None

    @property
    def is_chameleon_supported(self) -> "bool":
        """Indicate whether this artifact is maintained by Chameleon."""
        # We don't use a .filter here because .all is already used everywhere,
        # and if we use .all here, it's already cached.
        return any(l.label == Label.CHAMELEON_SUPPORTED for l in self.labels.all())

    @property
    def display_labels(self) -> "list[Label]":
        # We don't use a .filter here because .all is already used everywhere,
        # and if we use .all here, it's already cached.
        return [l for l in self.labels.all() if l.label != Label.CHAMELEON_SUPPORTED]


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

    def __str__(self):
        return f"{self.artifact.title} ({self.created_at})"


class ShareTarget(models.Model):
    artifact = models.ForeignKey(Artifact, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)


class DaypassRequest(models.Model):
    artifact_uuid = models.CharField(max_length=36, null=True)
    name = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    reason = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requestor"
    )

    STATUS_PENDING = "pending"
    STATUS_REJECTED = "rejected"
    STATUS_APPROVED = "approved"
    STATUS = (
        (STATUS_PENDING, "pending"),
        (STATUS_REJECTED, "rejected"),
        (STATUS_APPROVED, "approved"),
    )
    status = models.CharField(max_length=50, blank=False, choices=STATUS)
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decision_by",
        null=True,
    )
    decision_at = models.DateTimeField(null=True)
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE, null=True)


class DaypassProject(models.Model):
    """
    Stores the project where the user is added to when a daypass starts
    """

    artifact_uuid = models.CharField(max_length=36, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)


class FeaturedArtifact(models.Model):
    """
    Stores a link to an artifact in the Trovi API which is intended to be featured
    at the top of the Trovi page
    """

    artifact_uuid = models.UUIDField()

    def __repr__(self):
        from sharing_portal import trovi

        try:
            artifact = trovi.get_artifact_by_trovi_uuid(str(self.artifact_uuid))
        except trovi.TroviException:
            return f"Unknown artifact ({str(self.artifact_uuid)})"
        return f"{artifact['title']} ({artifact['uuid']})"

    def __str__(self):
        return repr(self)
