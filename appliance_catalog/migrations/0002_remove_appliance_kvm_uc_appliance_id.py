# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appliance',
            name='kvm_uc_appliance_id',
        ),
    ]
