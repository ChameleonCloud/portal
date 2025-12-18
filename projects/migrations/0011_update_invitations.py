from __future__ import unicode_literals

from django.db import migrations, models



class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_add_invitations'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='duration',
            field=models.IntegerField(null=True),
        ),
    ]
