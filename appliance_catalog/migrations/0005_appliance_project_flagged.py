# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0004_auto_20160119_2052'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='project_flagged',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
