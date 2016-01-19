# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='author_name',
            field=models.CharField(max_length=1000),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='chi_tacc_appliance_id',
            field=models.IntegerField(unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='chi_uc_appliance_id',
            field=models.IntegerField(unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='created_user',
            field=models.CharField(max_length=100, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='kvm_tacc_appliance_id',
            field=models.IntegerField(unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='name',
            field=models.CharField(max_length=100),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='support_contact_name',
            field=models.CharField(max_length=100),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='updated_user',
            field=models.CharField(max_length=100, null=True, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='version',
            field=models.CharField(max_length=100),
            preserve_default=True,
        ),
    ]
