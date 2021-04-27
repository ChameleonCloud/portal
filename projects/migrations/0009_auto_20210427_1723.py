# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-04-27 22:23
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import projects.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0008_auto_20200708_1116'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_issued', models.DateTimeField(auto_now_add=True)),
                ('date_expires', models.DateTimeField(default=projects.models.Invitation._generate_expiration, editable=False)),
                ('email_address', models.EmailField(max_length=254)),
                ('email_code', models.CharField(default=projects.models.Invitation._generate_secret, editable=False, max_length=26)),
                ('status', models.CharField(choices=[('ISSUED', 'Issued'), ('ACCEPTED', 'Accepted')], default='ISSUED', editable=False, max_length=30)),
                ('date_accepted', models.DateTimeField(editable=False, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='project',
            name='charge_code',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='invitation',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Project'),
        ),
        migrations.AddField(
            model_name='invitation',
            name='user_accepted',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='accepted_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='invitation',
            name='user_issued',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
    ]
