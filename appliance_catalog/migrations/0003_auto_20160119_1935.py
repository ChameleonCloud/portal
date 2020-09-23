# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliance_catalog', '0002_auto_20160114_2107'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliance',
            name='appliance_icon',
            field=models.ImageField(default=b'appliance_catalog/icons/default.svg', upload_to=b'appliance_catalog/icons/', blank=True),
            preserve_default=True,
        ),
    ]
