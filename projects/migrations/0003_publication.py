# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-29 18:39


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_auto_20190305_1632'),
    ]

    operations = [
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tas_project_id', models.IntegerField()),
                ('journal', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=500)),
                ('year', models.IntegerField()),
                ('author', models.CharField(max_length=100)),
                ('bibtex_source', models.TextField()),
                ('abstract', models.CharField(max_length=500)),
                ('added_by_username', models.CharField(max_length=100)),
                ('entry_created_date', models.DateField(auto_now_add=True)),
            ],
        ),
    ]
