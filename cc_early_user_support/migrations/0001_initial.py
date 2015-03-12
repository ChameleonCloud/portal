# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EarlyUserRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('justification', models.TextField()),
                ('request_status', models.CharField(default=b'REQ', max_length=3, choices=[(b'REQ', b'Requested'), (b'APP', b'Approved'), (b'DEN', b'Denied')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Early User Request',
                'verbose_name_plural': 'Early User Requests',
            },
            bases=(models.Model,),
        ),
    ]
