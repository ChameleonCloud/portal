# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectExtras',
            fields=[
                ('tas_project_id', models.IntegerField(serialize=False, primary_key=True)),
                ('charge_code', models.CharField(max_length=50)),
                ('nickname', models.CharField(max_length=50, null=True, blank=True)),
            ],
        ),
    ]
