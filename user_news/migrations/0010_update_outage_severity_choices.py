# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-17 19:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0009_py3'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outage',
            name='severity',
            field=models.CharField(choices=[('', ''), ('SEV-1', 'SEV-1'), ('SEV-2', 'SEV-2'), ('SEV-3', 'SEV-3')], default='', max_length=50),
        ),
    ]
