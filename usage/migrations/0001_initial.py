# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Downtime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('queue', models.CharField(max_length=50, choices=[(b'kvm@tacc', b'kvm@tacc'), (b'kvm@uc', b'kvm@uc'), (b'chi@tacc', b'chi@tacc'), (b'chi@uc', b'chi@uc')])),
                ('nodes_down', models.IntegerField(verbose_name=b'Num of nodes that are down')),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField(null=True, blank=True)),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.CharField(max_length=50, editable=False)),
                ('modified_by', models.CharField(max_length=50, editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
