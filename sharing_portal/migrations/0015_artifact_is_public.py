# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-25 20:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0014_deposition_repo_py3'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
