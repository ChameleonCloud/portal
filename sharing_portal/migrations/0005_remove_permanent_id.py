# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2019-11-13 02:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0004_artifact_versions_create_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='artifact',
            name='permanent_id',
        ),
    ]
