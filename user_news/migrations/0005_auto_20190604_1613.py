# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0004_auto_20190604_1559'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='registration_link',
            field=models.CharField(default=b'', max_length=500),
        ),
    ]
