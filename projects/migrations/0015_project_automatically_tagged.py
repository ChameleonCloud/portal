# Generated by Django 3.2 on 2022-09-01 21:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0014_remove_field_of_science"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="automatically_tagged",
            field=models.BooleanField(default=False),
        ),
    ]
