# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-29 18:39


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user_news', '0006_outage_severity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outage',
            name='severity',
            field=models.CharField(choices=[(b'', b''), (b'SEV-1', b'SEV-1'), (b'SEV-2', b'SEV-2')], default=b'', max_length=50),
        ),
        migrations.AlterField(
            model_name='usernewspluginmodel',
            name='cmsplugin_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='user_news_usernewspluginmodel', serialize=False, to='cms.CMSPlugin'),
        ),
    ]
