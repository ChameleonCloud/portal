from django.db import models
import json
import logging

logger = logging.getLogger('projects')

class ProjectExtras(models.Model):
    tas_project_id = models.IntegerField(primary_key=True)
    charge_code = models.CharField(max_length=50,blank=False,null=False)
    nickname = models.CharField(max_length=50,blank=False, null=False, unique=True)

class PublicationManager(models.Manager):

    def create_from_bibtex(self, bibtex_entry, project, username):
        pub = Publication()

        pub.tas_project_id = project.id
        if 'booktitle' in bibtex_entry:
            pub.booktitle = bibtex_entry.get('booktitle')
        if 'journal' in bibtex_entry:
            pub.journal = bibtex_entry.get('journal')
        if 'publisher' in bibtex_entry:
            pub.publisher = bibtex_entry.get('publisher')
        pub.title = bibtex_entry.get('title')
        pub.year = bibtex_entry.get('year')
        pub.author = bibtex_entry.get('author')
        if bibtex_entry.get('abstract'):
            pub.abstract =  bibtex_entry.get('abstract')
        pub.bibtex_source = json.dumps(bibtex_entry)
        pub.added_by_username = username
        pub.save()
        return pub

class Publication(models.Model):
    tas_project_id = models.IntegerField(null=False)
    journal =  models.CharField(max_length=500, null=True)
    publisher =  models.CharField(max_length=500, null=True)
    booktitle =  models.CharField(max_length=500, null=True)
    title =  models.CharField(max_length=500, null=False)
    year =  models.IntegerField(null=False)
    author =  models.CharField(max_length=500, null=False)
    bibtex_source = models.TextField()
    abstract =  models.TextField(blank=True,null=True)
    added_by_username = models.CharField(max_length=100)
    entry_created_date = models.DateField(auto_now_add=True)

    objects = PublicationManager()
