# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernewspluginmodel',
            name='display_events',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='usernewspluginmodel',
            name='display_news',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='usernewspluginmodel',
            name='display_outages',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
