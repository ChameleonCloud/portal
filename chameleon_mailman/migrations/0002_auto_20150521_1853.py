# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chameleon_mailman', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailmansubscription',
            name='users_list',
            field=models.BooleanField(default=True, help_text='Mailing list for discussion among Chameleon Users'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mailmansubscription',
            name='outage_notifications',
            field=models.BooleanField(default=True, help_text='Notifications about maintenance downtimes and outages'),
            preserve_default=True,
        ),
    ]
