# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0003_auto_20160119_1935'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='appliance_icon',
            field=models.ImageField(upload_to=b'appliance_catalog/icons/', blank=True),
            preserve_default=True,
        ),
    ]
