# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0007_appliance_documentation'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='short_description',
            field=models.CharField(default='', max_length=140),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='description',
            field=models.TextField(),
            preserve_default=True,
        ),
    ]
