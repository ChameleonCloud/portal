# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-25 20:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cc_early_user_support', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='earlyuserparticipant',
            name='participant_status',
            field=models.IntegerField(choices=[(0, 'Requested'), (1, 'Approved'), (2, 'Denied')], default=0),
        ),
        migrations.AlterField(
            model_name='earlyuserprogram',
            name='state',
            field=models.IntegerField(choices=[(0, 'Open'), (1, 'Active'), (2, 'Closed')], default=0),
        ),
    ]