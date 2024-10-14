# Generated by Django 4.2.16 on 2024-10-14 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0021_project_default_su_budget'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='joinrequest',
            name='join_request_user_link_unique_constraint',
        ),
        migrations.AlterField(
            model_name='publication',
            name='status',
            field=models.CharField(choices=[('SUBMITTED', 'Submitted'), ('APPROVED', 'Approved'), ('DUPLICATE', 'Duplicate'), ('REJECTED', 'Rejected'), ('DELETED', 'Deleted')], max_length=30),
        ),
        migrations.AlterField(
            model_name='publicationsource',
            name='approved_with',
            field=models.CharField(blank=True, choices=[('publication', 'Publication'), ('justification', 'Justification'), ('email', 'Email')], max_length=30, null=True),
        ),
    ]
