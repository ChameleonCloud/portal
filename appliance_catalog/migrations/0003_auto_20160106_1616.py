# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0002_remove_appliance_kvm_uc_appliance_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='updated_user',
            field=models.CharField(max_length=50, null=True, editable=False),
            preserve_default=True,
        ),
    ]
