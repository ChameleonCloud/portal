# Generated by Django 3.2 on 2023-08-07 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0020_artifactbadge_badge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='badge',
            name='name',
            field=models.CharField(choices=[('reproducible', 'reproducible'), ('chameleon', 'chameleon'), ('educational', 'educational')], max_length=50),
        ),
    ]
