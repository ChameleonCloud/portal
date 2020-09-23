# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0011_appliance_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='needs_review',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
