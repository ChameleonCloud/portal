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

        '''
            Required fields: journal, title, year, author
        '''
        logger.info('Journal Entry')
        logger.info(bibtex_entry.get('journal'))
        logger.info(bibtex_entry.get('title'))
        logger.info(bibtex_entry.get('year'))
        logger.info(bibtex_entry.get('author'))
        if not bibtex_entry.get('journal') or not bibtex_entry.get('title') or not bibtex_entry.get('year') \
            or not bibtex_entry.get('author'):
            logger.error('Missing one of required fields {journal, title, year, author} for bibtex entry: %s' \
                + json.dumps(bibtex_entry))
            return 'Entry is missing one of required fields {journal, title, year, author}'
        
        pub.tas_project_id = project.id
        pub.journal = bibtex_entry.get('journal')
        pub.title = bibtex_entry.get('title')
        pub.year = bibtex_entry.get('year')
        pub.author = bibtex_entry.get('author')
        pub.abstract =  bibtex_entry.get('abstract')
        pub.bibtex_source = json.dumps(bibtex_entry)
        pub.added_by_username = username
        pub.save()
        return pub

class Publication(models.Model):
    tas_project_id = models.IntegerField(null=False)
    journal =  models.CharField(max_length=100, null=False)
    title =  models.CharField(max_length=500, null=False)
    year =  models.IntegerField(null=False)
    author =  models.CharField(max_length=500, null=False)
    bibtex_source = models.TextField()
    abstract =  models.TextField(blank=True,null=True)
    added_by_username = models.CharField(max_length=100)
    entry_created_date = models.DateField(auto_now_add=True)

    objects = PublicationManager()
