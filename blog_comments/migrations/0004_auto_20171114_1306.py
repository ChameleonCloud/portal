# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog_comments', '0003_auto_20171106_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(related_query_name=b'comment', related_name='comments', to='djangocms_blog.Post'),
        ),
    ]
