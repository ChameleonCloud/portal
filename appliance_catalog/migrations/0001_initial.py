# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Appliance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(max_length=5000)),
                ('appliance_icon', models.ImageField(default=b'appliance_catalog/icons/default.png', upload_to=b'appliance_catalog/icons/', blank=True)),
                ('chi_tacc_appliance_id', models.IntegerField(null=True, blank=True)),
                ('chi_uc_appliance_id', models.IntegerField(null=True, blank=True)),
                ('kvm_tacc_appliance_id', models.IntegerField(null=True, blank=True)),
                ('author_name', models.CharField(max_length=50)),
                ('author_url', models.CharField(max_length=500)),
                ('support_contact_name', models.CharField(max_length=50)),
                ('support_contact_url', models.CharField(max_length=500)),
                ('project_supported', models.BooleanField(default=False)),
                ('version', models.CharField(max_length=50)),
                ('created_user', models.CharField(max_length=50, editable=False)),
                ('updated_user', models.CharField(max_length=50, null=True, editable=False)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ApplianceTagging',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('appliance', models.ForeignKey(to='appliance_catalog.Appliance', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Keyword',
            fields=[
                ('name', models.CharField(max_length=50, serialize=False, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='appliancetagging',
            name='keyword',
            field=models.ForeignKey(to='appliance_catalog.Keyword', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliance',
            name='keywords',
            field=models.ManyToManyField(to='appliance_catalog.Keyword', null=True, through='appliance_catalog.ApplianceTagging', blank=True),
            preserve_default=True,
        ),
    ]
