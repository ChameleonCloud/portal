# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('level', models.IntegerField(choices=[(20, b'Informational'), (25, b'Success'), (30, b'Warning'), (40, b'Error')])),
                ('title', models.CharField(max_length=80, blank=True)),
                ('message', models.TextField()),
                ('schedule_on', models.DateTimeField(verbose_name=b'scheduled display start', blank=True)),
                ('schedule_off', models.DateTimeField(verbose_name=b'scheduled display end', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
