# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Webinar',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('registration_open', models.DateTimeField()),
                ('registration_closed', models.DateTimeField()),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
            ],
            options={
                'verbose_name': 'Webinar',
                'verbose_name_plural': 'Webinars',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WebinarRegistrant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('webinar', models.ForeignKey(to='webinar_registration.Webinar', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Webinar Registrant',
                'verbose_name_plural': 'Webinar Registrants',
            },
            bases=(models.Model,),
        ),
    ]
