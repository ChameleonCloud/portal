from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings

import json

from ..models import Invitation

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
        migrations.AddField(
            model_name='invitation',
            name='date_exceeded_duration',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='email_address',
            field=models.EmailField(max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='email_code',
            field=models.CharField(default=Invitation._generate_secret, editable=False, max_length=26, null=True),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='date_expires',
            field=models.DateTimeField(default=Invitation._generate_expiration),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='user_issued',
            field=models.ForeignKey(editable=False, on_delete=models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL),
        ),
    ]
