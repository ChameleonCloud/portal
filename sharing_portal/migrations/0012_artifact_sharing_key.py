# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-08-20 18:41


from django.db import migrations, models
import sharing_portal.models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0011_drop_artifact_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='sharing_key',
            field=models.CharField(default=sharing_portal.models.gen_sharing_key, max_length=32, null=True),
        ),
    ]
