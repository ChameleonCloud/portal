# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-05-08 19:03


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Allocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_charge_code', models.CharField(max_length=50)),
                ('status', models.CharField(choices=[(b'inactive', b'expired or overused'), (b'active', b'active'), (b'pending', b'waiting for review decision'), (b'rejected', b'rejected'), (b'approved', b'approved but not active')], max_length=50)),
                ('justification', models.CharField(max_length=500, null=True)),
                ('date_requested', models.DateTimeField(null=True)),
                ('decision_summary', models.CharField(max_length=500, null=True)),
                ('date_reviewed', models.DateTimeField(null=True)),
                ('expiration_date', models.DateTimeField(null=True)),
                ('su_requested', models.FloatField()),
                ('start_date', models.DateTimeField()),
                ('su_allocated', models.FloatField()),
                ('su_used', models.FloatField()),
                ('requestor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='allocation_requestor', to=settings.AUTH_USER_MODEL)),
                ('reviewer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='allocation_reviewer', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
