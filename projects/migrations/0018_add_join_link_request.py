# Generated by Django 3.2 on 2023-03-30 16:36

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import projects.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0017_add_chameleon_publications_and_pi_aliases"),
    ]

    operations = [
        migrations.CreateModel(
            name="JoinLink",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "secret",
                    models.CharField(
                        default=projects.models._generate_secret,
                        max_length=26,
                        unique=True,
                    ),
                ),
                (
                    "project",
                    models.OneToOneField(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="join_link",
                        to="projects.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JoinRequest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=8,
                    ),
                ),
                ("decided_at", models.DateTimeField(null=True)),
                (
                    "join_link",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="join_requests",
                        to="projects.joinlink",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="join_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="joinrequest",
            constraint=models.UniqueConstraint(
                fields=("join_link", "user"),
                name="join_request_user_link_unique_constraint",
            ),
        ),
    ]
