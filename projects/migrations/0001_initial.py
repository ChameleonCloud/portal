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
                ('project_id', models.IntegerField(serialize=False, primary_key=True)),
                ('nickname', models.CharField(max_length=50, null=True, blank=True)),
            ],
        ),
    ]
