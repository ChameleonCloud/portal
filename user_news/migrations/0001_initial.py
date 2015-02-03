# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0003_auto_20140926_2347'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.SlugField(unique=True, max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('summary', ckeditor.fields.RichTextField(max_length=600)),
                ('body', ckeditor.fields.RichTextField()),
            ],
            options={
                'verbose_name': 'News',
                'verbose_name_plural': 'News',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('news_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='user_news.News')),
                ('event_type', models.TextField(choices=[(b'CONFERENCE', b'Conference'), (b'MEETING', b'Meeting'), (b'PAPER', b'Paper'), (b'POSTER', b'Poster'), (b'PRESENTATION', b'Presentation'), (b'TUTORIAL', b'Tutorial'), (b'WORKSHOP', b'Workshop'), (b'OTHER', b'Other')])),
                ('event_date', models.DateTimeField(verbose_name=b'event date')),
            ],
            options={
            },
            bases=('user_news.news',),
        ),
        migrations.CreateModel(
            name='NewsTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.TextField(max_length=50)),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Outage',
            fields=[
                ('news_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='user_news.News')),
                ('start_date', models.DateTimeField(verbose_name=b'start of outage')),
                ('end_date', models.DateTimeField(verbose_name=b'expected end of outage')),
            ],
            options={
            },
            bases=('user_news.news',),
        ),
        migrations.CreateModel(
            name='OutageUpdate',
            fields=[
                ('news_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='user_news.News')),
                ('original_item', models.ForeignKey(to='user_news.Outage')),
            ],
            options={
            },
            bases=('user_news.news',),
        ),
        migrations.CreateModel(
            name='UserNewsPluginModel',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('limit', models.IntegerField(default=5)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.AddField(
            model_name='news',
            name='author',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='news',
            name='tags',
            field=models.ManyToManyField(to='user_news.NewsTag', blank=True),
            preserve_default=True,
        ),
    ]
