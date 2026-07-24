import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chameleon", "0014_dataset_datasetdownloadevent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Reviewer",
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
                    "review_type",
                    models.CharField(
                        choices=[
                            ("allocation", "Allocation"),
                            ("pi_eligibility", "PI Eligibility"),
                            ("publication", "Publication"),
                        ],
                        max_length=50,
                        unique=True,
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"is_staff": True},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
