# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-16 19:44
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chameleon', '0002_auto_20200601_1546'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userproperties',
            name='is_pi',
        ),
        migrations.AddField(
            model_name='userproperties',
            name='pi_decision_summary',
            field=models.TextField(default=None),
        ),
        migrations.AddField(
            model_name='userproperties',
            name='pi_eligibility',
            field=models.CharField(choices=[(b'INELIGIBLE', b'Ineligible'), (b'ELIGIBLE', b'Eligible')], default=b'INELIGIBLE', max_length=50),
        ),
        migrations.AddField(
            model_name='userproperties',
            name='pi_requested_at',
            field=models.DateTimeField(default=None, verbose_name=b'Date Requested'),
        ),
        migrations.AddField(
            model_name='userproperties',
            name='pi_reviewed_at',
            field=models.DateTimeField(default=None, verbose_name=b'Date Reviewed'),
        ),
        migrations.AddField(
            model_name='userproperties',
            name='pi_reviewer',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
    ]