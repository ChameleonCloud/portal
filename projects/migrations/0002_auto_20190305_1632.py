# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectextras',
            name='nickname',
            field=models.CharField(unique=True, max_length=50),
        ),
    ]
