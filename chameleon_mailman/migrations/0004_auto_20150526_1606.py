# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('chameleon_mailman', '0003_auto_20150522_2056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailmansubscription',
            name='user',
            field=models.OneToOneField(related_name='subscriptions', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
