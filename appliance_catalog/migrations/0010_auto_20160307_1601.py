# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0009_auto_20160307_1541'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appliance',
            name='created_user',
        ),
        migrations.RemoveField(
            model_name='appliance',
            name='updated_user',
        ),
    ]
