import json
import logging
import secrets
from operator import attrgetter
from datetime import timedelta
import pydetex.pipelines as pip

from django.conf import settings
from django.db import models
from django.utils import timezone

from projects.user_publication.utils import PublicationUtils

logger = logging.getLogger(__name__)


# DEPRECATED (needs to be removed, but kept for migration)
class Type(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)
    description = models.CharField(max_length=255, blank=False, unique=True)
    expose = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    tag = models.ForeignKey(
        Tag, related_name="projects", null=True, on_delete=models.CASCADE
    )
    automatically_tagged = models.BooleanField(default=False)
    description = models.TextField()
    pi = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="project_pi", on_delete=models.CASCADE
    )
    title = models.TextField(blank=False)
    nickname = models.CharField(max_length=255, blank=False, unique=True)
    charge_code = models.CharField(max_length=50, blank=False, unique=True)

    def __str__(self) -> str:
        return self.charge_code

    def as_dict(self, **kwargs):
        return Project.to_dict(self, **kwargs)

    @classmethod
    def to_dict(cls, proj, fetch_allocations=True, alloc_status=None):
        if alloc_status is None:
            alloc_status = []
        json_proj = {
            "description": proj.description,
            "piId": proj.pi.id,
            "title": proj.title,
            "nickname": proj.nickname,
            "chargeCode": proj.charge_code,
            "tagId": proj.tag.id if proj.tag else None,
            "tag": f"{proj.tag.name} — {proj.tag.description}" if proj.tag else None,
            "allocations": [],
            "source": "Chameleon",
            "pi": proj.pi.as_dict(role="PI"),
            "id": proj.id,
        }

        if fetch_allocations:
            allocations_qs = proj.allocations.all()
            # NOTE(jason): we cannot sort using .order_by().reverse() or any
            # other Django ORM utility here! It will break the prefetch_related
            # behavior and cause a huge performance degradation.
            # We can ONLY do proj.allocations.all() -- this is because we have
            # already called this function when (possibly) fetching allocation
            # balances, and we store the balance counters over top of the DB
            # values in that case. If we do a different type of query, those
            # cached values get effectively ignored. This is pretty hacky; we
            # should probably somehow store the pre-fetched balances in a
            # separate structure and pull it in here somehow.
            allocs = sorted(
                allocations_qs, key=attrgetter("date_requested"), reverse=True
            )
            if alloc_status:
                allocs = [a for a in allocs if a.status in alloc_status]
            json_proj["allocations"] = [a.as_dict() for a in allocs]

        return json_proj

    def __hash__(self):
        return hash(self.id)


class ProjectExtras(models.Model):
    tas_project_id = models.IntegerField(primary_key=True)
    charge_code = models.CharField(max_length=50, blank=False, null=False)
    nickname = models.CharField(max_length=50, blank=False, null=False, unique=True)


class ProjectPIAlias(models.Model):
    pi = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="pi", on_delete=models.CASCADE
    )
    alias = models.CharField(max_length=100)


class InvitationQuerySet(models.QuerySet):
    pass


class InvitationManager(models.Manager):
    pass


class Invitation(models.Model):
    """Model to hold invitations of users to projects."""

    STATUS_ISSUED = "ISSUED"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_BEYOND_DURATION = "BEYOND_DURATION"
    STATUSES = [
        (STATUS_ISSUED, "Issued"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_BEYOND_DURATION, "Beyond Duration"),
    ]

    @staticmethod
    def default_days_until_expiration():
        return 30

    def _generate_secret():
        """Generate secure code.

        https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe
        Each byte creates 1.3 characters on average, but we need to store into
        a fixed length field. Using nchars for both bytes and characters ensures
        that we always have sufficient randomness, but will fit in the db field.
        As of 2021, a resonable standard is 20 bytes of randomness, or 26 characters.
        """
        nbytes = 26
        nchars = nbytes
        return secrets.token_urlsafe(nbytes)[:nchars]

    def _generate_expiration():
        now = timezone.now()
        duration = timezone.timedelta(days=Invitation.default_days_until_expiration())
        return now + duration

    # This information is needed on creation
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user_issued = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, editable=False
    )
    date_issued = models.DateTimeField(auto_now_add=True, editable=False)
    date_expires = models.DateTimeField(default=_generate_expiration, editable=True)
    email_address = models.EmailField(null=True)
    email_code = models.CharField(
        max_length=26, default=_generate_secret, editable=False, null=True
    )

    status = models.CharField(
        choices=STATUSES, max_length=30, default=STATUS_ISSUED, editable=False
    )

    # This information is filled on response
    user_accepted = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="accepted_user",
        editable=False,
        null=True,
    )
    date_accepted = models.DateTimeField(auto_now_add=False, editable=False, null=True)
    duration = models.IntegerField(null=True)

    def date_exceeds_duration(self):
        return self.date_accepted + timedelta(hours=self.duration)

    def __str__(self) -> str:
        return f"{self.email_address}, {self.email_code}, {self.status}, {'EXPIRED' if self._is_expired() else self.date_expires}"

    objects = InvitationManager()

    def accept(self, user):
        self.status = Invitation.STATUS_ACCEPTED
        self.date_accepted = timezone.now()
        self.user_accepted = user
        self.save()

    def get_cant_accept_reason(self):
        if not self._is_accepted():
            return "This invitation has already been accepted!"
        elif not self._is_expired():
            return "This invitation has expired!"

    def can_accept(self):
        return not self._is_accepted() and not self._is_expired()

    def _is_accepted(self):
        return self.status == Invitation.STATUS_ACCEPTED

    def _is_expired(self):
        return self.date_expires < timezone.now()


class PublicationManager(models.Manager):
    def create_from_bibtex(self, bibtex_entry, project, username, source, status):
        pub = Publication()

        pub.project_id = project.id

        pub.publication_type = PublicationUtils.get_pub_type(bibtex_entry)
        pub.title = pip.strict(bibtex_entry.get("title", ""))
        pub.year = bibtex_entry.get("year")
        pub.month = PublicationUtils.get_month(bibtex_entry)
        pub.author = pip.strict(bibtex_entry.get("author", ""))
        pub.bibtex_source = json.dumps(bibtex_entry)
        pub.added_by_username = username
        pub.forum = PublicationUtils.get_forum(bibtex_entry)
        pub.link = PublicationUtils.get_link(bibtex_entry)
        pub.doi = bibtex_entry.get("doi")
        pub.status = status

        pub.save()
        PublicationSource.objects.create(name=source, publication=pub, is_source=True)
        return pub


class Publication(models.Model):
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_DUPLICATE = "DUPLICATE"
    STATUS_REJECTED = "REJECTED"

    STATUSES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DUPLICATE, "Duplicate"),
        (STATUS_REJECTED, "Rejected"),
    ]

    # keys to report in __repr__
    PUBLICATION_REPORT_FIELDS = [
        "id",
        "title",
        "author",
        "year",
        "publication_type",
        "forum",
        "bibtex_source",
        "link",
        "doi",
        "status",
    ]

    tas_project_id = models.IntegerField(null=True)
    project = models.ForeignKey(
        Project, related_name="project_publication", null=True, on_delete=models.CASCADE
    )
    publication_type = models.CharField(max_length=50, null=False)
    forum = models.CharField(max_length=500, null=True, blank=True)
    title = models.CharField(max_length=500, null=False)
    year = models.IntegerField(null=False)
    month = models.IntegerField(null=True, blank=True)
    author = models.CharField(max_length=500, null=False)
    bibtex_source = models.TextField()
    link = models.CharField(max_length=500, null=True, blank=True)
    added_by_username = models.CharField(max_length=100)
    doi = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(choices=STATUSES, max_length=30, null=False)
    checked_for_duplicates = models.BooleanField(default=False, null=False)

    def __str__(self) -> str:
        return f"{self.id} {self.title}, {self.author}, In {self.forum}. {self.year}"

    def __repr__(self) -> str:
        line_format = "{0:18} : {1}"
        lines = [
            line_format.format(ck, getattr(self, ck))
            for ck in self.PUBLICATION_REPORT_FIELDS
        ]
        return "\n" + "\n".join(lines)

    objects = PublicationManager()


class ChameleonPublication(models.Model):
    title = models.CharField(max_length=500, null=False)
    ref = models.CharField(max_length=40, null=True)


class Funding(models.Model):
    project = models.ForeignKey(
        Project, related_name="project_funding", null=True, on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=True, null=False)
    agency = models.CharField(max_length=200, null=False)
    award = models.CharField(max_length=200, null=True)
    grant_name = models.CharField(max_length=500, null=True)

    def __str__(self) -> str:
        return f"{self.agency} {self.award}-{self.grant_name}"


class PublicationSource(models.Model):
    """Model to hold information about source of publication and number of citations"""

    USER_REPORTED = "user_reported"
    SCOPUS = "scopus"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    GOOGLE_SCHOLAR = "google_scholar"

    SOURCES = [
        (USER_REPORTED, "User Reported"),
        (SCOPUS, "Scopus"),
        (SEMANTIC_SCHOLAR, "Semantic scholar"),
        (GOOGLE_SCHOLAR, "Google Scholar"),
    ]

    APPROVED_WITH_PUBLICATION = "publication"
    APPROVED_WITH_JUSTIFICATION = "justification"
    APPROVED_WITH_EMAIL = "email"

    APPROVED_WITH = [
        (APPROVED_WITH_PUBLICATION, "Publication"),
        (APPROVED_WITH_JUSTIFICATION, "Justification"),
        (APPROVED_WITH_EMAIL, "Email"),
    ]

    SOURCE_REPORT_FIELDS = [
        "name",
        "is_found_by_algorithm",
        "cites_chameleon",
        "acknowledges_chameleon",
        "approved_with",
    ]

    publication = models.ForeignKey(
        Publication, related_name="sources", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=30, choices=SOURCES)
    citation_count = models.IntegerField(default=0, null=False)
    # auto_add_now does not allow to insert with a custom datetime
    entry_created_date = models.DateField(default=timezone.now)
    # if the publication identified by the source
    # using our algorithm to find publications ref Chamaeleon
    is_found_by_algorithm = models.BooleanField(default=False, null=False)
    cites_chameleon = models.BooleanField(default=False, null=False)
    acknowledges_chameleon = models.BooleanField(default=False, null=False)
    approved_with = models.CharField(choices=APPROVED_WITH, max_length=30, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "name"], name="Unique source for a publication"
            ),
            models.CheckConstraint(
            # if the publication is approved then approved_with must have a value
                check=(
                    models.Q(publication__status=Publication.STATUS_APPROVED, approved_with__isnull=False)
                    | ~models.Q(publication__status=Publication.STATUS_APPROVED)
                ),
                name='valid_approved_with_for_approved_status'
            )
        ]

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        line_format = "{0:24} : {1}"
        lines = [
            line_format.format(ck, getattr(self, ck))
            for ck in self.SOURCE_REPORT_FIELDS
        ]
        return "\n" + "\n".join(lines)


class PublicationDuplicate(models.Model):
    """Model to hold information about duplicate publications"""

    duplicate = models.ForeignKey(
        Publication, related_name="duplicate_of", on_delete=models.CASCADE
    )
    original = models.ForeignKey(
        Publication, related_name="duplicates", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["duplicate", "original"],
                name="Unique duplicate to its duplicate of publication",
            )
        ]
