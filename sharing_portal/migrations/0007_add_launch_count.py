# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-07-29 23:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0006_author_optional_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='launch_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='artifactversion',
            name='launch_count',
            field=models.IntegerField(default=0),
        ),
    ]
