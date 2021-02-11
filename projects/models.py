import json
import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger("projects")


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


class ProjectExtras(models.Model):
    tas_project_id = models.IntegerField(primary_key=True)
    charge_code = models.CharField(max_length=50, blank=False, null=False)
    nickname = models.CharField(max_length=50, blank=False, null=False, unique=True)


class PublicationManager(models.Manager):
    def create_from_bibtex(self, bibtex_entry, project, username):
        pub = Publication()

        pub.project_id = project.id
        if "booktitle" in bibtex_entry:
            pub.booktitle = bibtex_entry.get("booktitle")
        if "journal" in bibtex_entry:
            pub.journal = bibtex_entry.get("journal")
        if "publisher" in bibtex_entry:
            pub.publisher = bibtex_entry.get("publisher")
        pub.title = bibtex_entry.get("title")
        pub.year = bibtex_entry.get("year")
        pub.author = bibtex_entry.get("author")
        if bibtex_entry.get("abstract"):
            pub.abstract = bibtex_entry.get("abstract")
        pub.bibtex_source = json.dumps(bibtex_entry)
        pub.added_by_username = username
        pub.save()
        return pub


class Publication(models.Model):
    tas_project_id = models.IntegerField(null=True)
    project = models.ForeignKey(Project, related_name="project_publication", null=True)
    journal = models.CharField(max_length=500, null=True)
    publisher = models.CharField(max_length=500, null=True)
    booktitle = models.CharField(max_length=500, null=True)
    title = models.CharField(max_length=500, null=False)
    year = models.IntegerField(null=False)
    author = models.CharField(max_length=500, null=False)
    bibtex_source = models.TextField()
    abstract = models.TextField(blank=True, null=True)
    added_by_username = models.CharField(max_length=100)
    entry_created_date = models.DateField(auto_now_add=True)

    objects = PublicationManager()
