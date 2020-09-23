# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0005_auto_20190604_1613'),
    ]

    operations = [
        migrations.AddField(
            model_name='outage',
            name='severity',
            field=models.CharField(default=b'', max_length=50, choices=[(b'SEV-1', b'SEV-1'), (b'SEV-2', b'SEV-2')]),
        ),
    ]
