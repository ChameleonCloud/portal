from django.conf import settings
from django.db import models
import json
from operator import attrgetter

from projects.pub_utils import PublicationUtils


class Type(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)


class Field(models.Model):
    name = models.CharField(max_length=255, blank=False, unique=True)


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
    charge_code = models.CharField(max_length=50, blank=False)

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
