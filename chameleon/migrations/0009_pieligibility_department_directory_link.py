# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-05 18:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chameleon', '0008_auto_20210119_1925'),
    ]

    operations = [
        migrations.AddField(
            model_name='pieligibility',
            name='department_directory_link',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
