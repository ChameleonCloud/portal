# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangoRT', '0002_auto_20160224_2223'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticketcategories',
            name='category',
        ),
        migrations.AddField(
            model_name='ticketcategories',
            name='category_display_name',
            field=models.CharField(default=b'', max_length=200),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ticketcategories',
            name='category_field_name',
            field=models.CharField(default=b'', max_length=200),
            preserve_default=True,
        ),
    ]
