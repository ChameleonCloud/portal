# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Appliance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(max_length=5000)),
                ('appliance_icon', models.ImageField(default=b'appliance_catalog/icons/default.jpg', upload_to=b'appliance_catalog/icons/')),
                ('chi_tacc_appliance_id', models.IntegerField(null=True)),
                ('chi_uc_appliance_id', models.IntegerField(null=True)),
                ('kvm_tacc_appliance_id', models.IntegerField(null=True)),
                ('kvm_uc_appliance_id', models.IntegerField(null=True)),
                ('author_name', models.CharField(max_length=50)),
                ('author_url', models.CharField(max_length=500)),
                ('support_contact_name', models.CharField(max_length=50)),
                ('support_contact_url', models.CharField(max_length=500)),
                ('project_supported', models.BooleanField(default=False)),
                ('version', models.CharField(max_length=50)),
                ('created_user', models.CharField(max_length=50, editable=False)),
                ('updated_user', models.CharField(max_length=50, editable=False)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Keyword',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='appliance',
            name='keywords',
            field=models.ManyToManyField(to='appliance_catalog.Keyword'),
            preserve_default=True,
        ),
    ]
