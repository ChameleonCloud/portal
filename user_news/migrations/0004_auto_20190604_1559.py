# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0003_outage_resolved'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='registration_link',
            field=models.CharField(default='', max_length=500),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.TextField(choices=[(b'WEBINAR', b'Webinar'), (b'CONFERENCE', b'Conference'), (b'MEETING', b'Meeting'), (b'PAPER', b'Paper'), (b'POSTER', b'Poster'), (b'PRESENTATION', b'Presentation'), (b'TUTORIAL', b'Tutorial'), (b'WORKSHOP', b'Workshop'), (b'OTHER', b'Other')]),
        ),
    ]
