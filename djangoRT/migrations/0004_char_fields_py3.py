# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-02-25 20:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangoRT', '0003_auto_20160224_2227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketcategories',
            name='category_display_name',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='ticketcategories',
            name='category_field_name',
            field=models.CharField(default='', max_length=200),
        ),
    ]