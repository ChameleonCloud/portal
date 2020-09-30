# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0012_appliance_needs_review'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='keywords',
            field=models.ManyToManyField(to='appliance_catalog.Keyword', through='appliance_catalog.ApplianceTagging', blank=True),
        ),
    ]
