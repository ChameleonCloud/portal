# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0006_auto_20160122_2208'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='documentation',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
