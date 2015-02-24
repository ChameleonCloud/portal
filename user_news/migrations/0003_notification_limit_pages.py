# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0002_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='limit_pages',
            field=models.TextField(verbose_name=b'Limit display only to these page paths (one per line)', blank=True),
            preserve_default=True,
        ),
    ]
