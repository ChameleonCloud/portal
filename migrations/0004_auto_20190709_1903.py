# Generated by Django 2.2.2 on 2019-07-09 19:03

from django.db import migrations, models
import sharing.models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0003_auto_20190708_1611'),
    ]

    operations = [
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', sharing.models.LabelField(max_length=50)),
            ],
            options={
                'ordering': ('label',),
            },
        ),
        migrations.AlterField(
            model_name='artifact',
            name='DOI',
            field=models.CharField(blank=True, max_length=50, null=True, validators=[sharing.models.Artifact.validate_doi]),
        ),
        migrations.AlterField(
            model_name='artifact',
            name='description',
            field=models.TextField(max_length=5000),
        ),
        migrations.AlterField(
            model_name='artifact',
            name='git_repo',
            field=models.CharField(blank=True, max_length=200, null=True, validators=[sharing.models.Artifact.validate_git_repo]),
        ),
        migrations.AddField(
            model_name='artifact',
            name='labels',
            field=models.ManyToManyField(blank=True, null=True, related_name='artifacts', to='sharing.Label'),
        ),
    ]
