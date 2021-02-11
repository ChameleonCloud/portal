# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('appliance_catalog', '0008_auto_20160210_2051'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='created_by',
            field=models.ForeignKey(related_name='appliances', default=1, to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE,),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='appliance',
            name='updated_by',
            field=models.ForeignKey(default=1, to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE,),
            preserve_default=False,
        ),
        migrations.RunSQL(
            'UPDATE appliance_catalog_appliance SET created_by_id = ('
            'SELECT u.id FROM auth_user u '
            'WHERE u.username = appliance_catalog_appliance.created_user);'
        ),
        migrations.RunSQL(
            'UPDATE appliance_catalog_appliance SET updated_by_id = ('
            'SELECT u.id FROM auth_user u '
            'WHERE u.username = appliance_catalog_appliance.updated_user);'
        ),
    ]
