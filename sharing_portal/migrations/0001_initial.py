# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-09-12 22:54
from __future__ import unicode_literals

from django.db import migrations, models
import sharing_portal.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('short_description', models.CharField(blank=True, max_length=70, null=True)),
                ('description', models.TextField(max_length=5000)),
                ('image', models.ImageField(blank=True, null=True, upload_to=b'sharing_portal/images/')),
                ('doi', models.CharField(blank=True, max_length=50, null=True, validators=[sharing_portal.models.validate_zenodo_doi])),
                ('permanent_id', models.CharField(blank=True, default=b'', editable=False, max_length=50)),
                ('git_repo', models.CharField(blank=True, max_length=200, null=True, validators=[sharing_portal.models.validate_git_repo])),
                ('launchable', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('associated_artifacts', models.ManyToManyField(blank=True, related_name='associated', to='sharing_portal.Artifact')),
            ],
            options={
                'ordering': ('title',),
            },
        ),
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('first_name', models.CharField(max_length=200)),
                ('last_name', models.CharField(max_length=200)),
                ('full_name', models.CharField(editable=False, max_length=600)),
            ],
            options={
                'ordering': ('last_name',),
            },
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', sharing_portal.models.LabelField(max_length=50)),
            ],
            options={
                'ordering': ('label',),
            },
        ),
        migrations.AddField(
            model_name='artifact',
            name='authors',
            field=models.ManyToManyField(related_name='artifacts', to='sharing_portal.Author'),
        ),
        migrations.AddField(
            model_name='artifact',
            name='labels',
            field=models.ManyToManyField(blank=True, related_name='artifacts', to='sharing_portal.Label'),
        ),
    ]