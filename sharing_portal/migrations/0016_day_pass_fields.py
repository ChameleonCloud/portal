# Generated by Django 3.2 on 2021-09-08 20:08

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharing_portal', '0015_artifact_is_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='is_reproducible',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='artifact',
            name='reproduce_hours',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='artifact',
            name='project',
            field=models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, related_name='belongs_to_project', to='projects.project'),
        ),
        migrations.AddField(
            model_name='artifact',
            name='reproducibility_project',
            field=models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, related_name='reproducibility_project', to='projects.project'),
        ),
        migrations.CreateModel(
            name='DaypassRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('institution', models.CharField(max_length=200)),
                ('reason', models.TextField(max_length=5000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('rejected', 'rejected'), ('approved', 'approved')], max_length=50)),
                ('decision_at', models.DateTimeField(null=True)),
                ('artifact', models.ForeignKey(on_delete=models.deletion.CASCADE, to='sharing_portal.artifact')),
                ('created_by', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='requestor', to=settings.AUTH_USER_MODEL)),
                ('decision_by', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='decision_by', to=settings.AUTH_USER_MODEL, null=True)),
                ('invitation', models.ForeignKey(null=True, on_delete=models.deletion.CASCADE, to='projects.invitation')),
            ],
        ),
    ]
