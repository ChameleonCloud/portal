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
            name='EarlyUserParticipant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('justification', models.TextField()),
                ('participant_status', models.IntegerField(default=0, choices=[(0, b'Requested'), (1, b'Approved'), (2, b'Denied')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Early User Participant',
                'verbose_name_plural': 'Early User Participants',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EarlyUserProgram',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('state', models.IntegerField(default=0, choices=[(0, b'Open'), (1, b'Active'), (2, b'Closed')])),
            ],
            options={
                'verbose_name': 'Early User Program',
                'verbose_name_plural': 'Early User Programs',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='earlyuserparticipant',
            name='program',
            field=models.ForeignKey(to='cc_early_user_support.EarlyUserProgram'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='earlyuserparticipant',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
