# Generated by Django 3.2 on 2022-03-04 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0016_day_pass_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='trovi_uuid',
            field=models.CharField(max_length=36, null=True),
        ),
    ]
