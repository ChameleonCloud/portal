# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0010_auto_20160307_1601'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='template',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
