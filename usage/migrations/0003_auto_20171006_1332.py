# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usage', '0002_auto_20160218_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downtime',
            name='queue',
            field=models.CharField(max_length=50, choices=[(b'kvm@tacc', b'kvm@tacc'), (b'chi@tacc', b'chi@tacc'), (b'chi@uc', b'chi@uc')]),
            preserve_default=True,
        ),
    ]
