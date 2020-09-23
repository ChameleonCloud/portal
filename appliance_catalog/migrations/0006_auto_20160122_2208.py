# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0005_appliance_project_flagged'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='chi_tacc_appliance_id',
            field=models.CharField(max_length=100, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='chi_uc_appliance_id',
            field=models.CharField(max_length=100, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='appliance',
            name='kvm_tacc_appliance_id',
            field=models.CharField(max_length=100, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
    ]
