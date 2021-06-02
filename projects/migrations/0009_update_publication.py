# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-25 21:44
from __future__ import unicode_literals

from django.db import migrations, models

import json

from projects.pub_utils import PublicationUtils

def migrate_to_publication_fields(apps, schema_editor):
    Publication = apps.get_model('projects', 'Publication')

    # reparse bibtex_source field to fill in new fields
    for pub in Publication.objects.all():
        bibtex_entry = json.loads(pub.bibtex_source)
        pub.publication_type = bibtex_entry.get("ENTRYTYPE")
        pub.month = PublicationUtils.get_month(bibtex_entry)    
        pub.forum = PublicationUtils.get_forum(bibtex_entry)
        pub.link = PublicationUtils.get_link(bibtex_entry)
        pub.save()

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_auto_20200708_1116'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='publication',
            name='booktitle',
        ),
        migrations.RemoveField(
            model_name='publication',
            name='abstract',
        ),
        migrations.RemoveField(
            model_name='publication',
            name='journal',
        ),
        migrations.RemoveField(
            model_name='publication',
            name='publisher',
        ),
        migrations.AddField(
            model_name='publication',
            name='forum',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='publication',
            name='link',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='publication',
            name='month',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='publication',
            name='publication_type',
            field=models.CharField(default='article', max_length=50),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_to_publication_fields),
    ]
