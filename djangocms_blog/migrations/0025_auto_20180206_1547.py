# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_blog', '0024_post_featured_post'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='featured_post',
            field=models.BooleanField(default=False, verbose_name='Featured Post'),
        ),
    ]
