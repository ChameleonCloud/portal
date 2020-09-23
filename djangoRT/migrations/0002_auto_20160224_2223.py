# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangoRT', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticketcategories',
            name='category_field_name',
        ),
        migrations.RemoveField(
            model_name='ticketcategories',
            name='category_friendly_name',
        ),
        migrations.AddField(
            model_name='ticketcategories',
            name='category',
            field=models.CharField(default=(b'', b'Choose a category'), max_length=200, choices=[(b'', b'Choose a category')]),
            preserve_default=True,
        ),
    ]
