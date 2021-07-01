import json
import logging
import secrets
from operator import attrgetter

<<<<<<< HEAD
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)
=======
from projects.pub_utils import PublicationUtils

>>>>>>> master

class Type(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)

    def __str__(self) -> str:
        return self.name


class Field(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)

    def __str__(self) -> str:
        return self.name


class FieldHierarchy(models.Model):
    parent = models.ForeignKey(Field, related_name="field_parent")
    child = models.ForeignKey(Field, related_name="field_child")

    class Meta:
        unique_together = ("parent", "child")


class Project(models.Model):
    type = models.ForeignKey(Type, related_name="project_type")
    description = models.TextField()
    pi = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="project_pi")
    title = models.TextField(blank=False)
    nickname = models.CharField(max_length=255, blank=False, unique=True)
    field = models.ForeignKey(Field, related_name="project_field", null=True)
    charge_code = models.CharField(max_length=50, blank=False, unique=True)

    def __str__(self) -> str:
        return self.charge_code

    def as_tas(self, **kwargs):
        return Project.to_tas(self, **kwargs)

    @classmethod
    def to_tas(cls, proj, fetch_allocations=True, alloc_status=[]):
        tas_proj = {
            "description": proj.description,
            "piId": proj.pi_id,
            "title": proj.title,
            "nickname": proj.nickname,
            "chargeCode": proj.charge_code,
            "typeId": proj.type_id,
            "fieldId": proj.field_id,
            "type": proj.type.name if proj.type else None,
            "field": proj.field.name if proj.field else None,
            "allocations": [],
            "source": "Chameleon",
            "pi": proj.pi.as_tas(role="PI"),
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
            tas_proj["allocations"] = [a.as_tas() for a in allocs]

        return tas_proj


class ProjectExtras(models.Model):
    tas_project_id = models.IntegerField(primary_key=True)
    charge_code = models.CharField(max_length=50, blank=False, null=False)
    nickname = models.CharField(max_length=50, blank=False, null=False, unique=True)


class InvitationQuerySet(models.QuerySet):
    pass


class InvitationManager(models.Manager):
    pass


class Invitation(models.Model):
    """Model to hold invitations of users to projects."""

    STATUS_ISSUED = "ISSUED"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUSES = [(STATUS_ISSUED, "Issued"), (STATUS_ACCEPTED, "Accepted")]

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
    email_address = models.EmailField(blank=False)
    email_code = models.CharField(
        max_length=26, default=_generate_secret, editable=False
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
    def create_from_bibtex(self, bibtex_entry, project, username):
        pub = Publication()

        pub.project_id = project.id

        pub.publication_type = bibtex_entry.get("ENTRYTYPE")
        pub.title = bibtex_entry.get("title")
        pub.year = bibtex_entry.get("year")
        pub.month = PublicationUtils.get_month(bibtex_entry)
        pub.author = bibtex_entry.get("author")
        pub.bibtex_source = json.dumps(bibtex_entry)
        pub.added_by_username = username
        pub.forum = PublicationUtils.get_forum(bibtex_entry)
        pub.link = PublicationUtils.get_link(bibtex_entry)

        pub.save()
        return pub


class Publication(models.Model):
    tas_project_id = models.IntegerField(null=True)
    project = models.ForeignKey(Project, related_name="project_publication", null=True)
    publication_type = models.CharField(max_length=50, null=False)
    forum = models.CharField(max_length=500, null=True)
    title = models.CharField(max_length=500, null=False)
    year = models.IntegerField(null=False)
    month = models.IntegerField(null=True)
    author = models.CharField(max_length=500, null=False)
    bibtex_source = models.TextField()
    link = models.CharField(max_length=500, null=True)
    added_by_username = models.CharField(max_length=100)
    entry_created_date = models.DateField(auto_now_add=True)

    objects = PublicationManager()
