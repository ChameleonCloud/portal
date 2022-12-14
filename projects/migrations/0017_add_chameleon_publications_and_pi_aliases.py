# Generated by Django 3.2 on 2022-12-12 21:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CHAMELEON_PUBLICATIONS = [
    {
        "title": "lessons learned from the chameleon testbed",
        "ref": "18f4a526234fbfed639b3788703d43fa6b468d9b",
    },
    {
        "title": "chameleon: a large-scale, deeply reconfigurable testbed for computer science research",
        "ref": "1c91f729e7f51cb6fb709dfedcddb9bde10d1914",
    },
    {"title": "chameleon@edge community workshop report"},
    {"title": "operational lessons from chameleon"},
    {
        "title": "application-based qos support with p4 and openflow: a demonstration using chameleon"
    },
    {"title": "application-based qoe support with p4 and openflow"},
    {
        "title": "overcast: running controlled experiments spanning research and commercial clouds"
    },
    {"title": "managing allocatable resources"},
    {"title": "a case for integrating experimental containers with notebooks"},
    {"title": "managing allocatable resources ( invited paper )"},
    {
        "title": "next generation clouds, the chameleon cloud testbed, and software defined networking (sdn)",
        "ref": "6738ab2ba7ab2971153fd951e02af62e43b15e5b",
    },
    {"title": "chi-in-a-box: reducing operational costs of research testbeds"},
    {"title": "migrating towards single sign-on and federated identity"},
    {
        "title": "Chameleon: A Scalable Production Testbed for Computer Science Research",
        "ref": "1c91f729e7f51cb6fb709dfedcddb9bde10d1914",
    },
]

PI_ALIASES = [
    {"pi_id": 6676, "alias": "Vijay Chidambaram"}
]


def create_chameleon_publications(apps, _):
    chameleon_publication_model = apps.get_model("projects", "ChameleonPublication")
    if chameleon_publication_model.objects.exists():
        return
    chameleon_publication_model.objects.bulk_create(
        chameleon_publication_model(**pub) for pub in CHAMELEON_PUBLICATIONS
    )

def create_pi_aliases(apps, _):
    pi_alias_model = apps.get_model("projects", "ProjectPIAlias")
    if pi_alias_model.objects.exists():
        return
    pi_alias_model.objects.bulk_create(pi_alias_model(**alias) for alias in PI_ALIASES)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0016_publication_source_of_truth"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChameleonPublication",
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
                ("title", models.CharField(max_length=500)),
                ("ref", models.CharField(max_length=40, null=True)),
            ],
        ),
        migrations.RunPython(create_chameleon_publications),
        migrations.CreateModel(
            name="ProjectPIAlias",
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
                ("alias", models.CharField(max_length=100)),
                (
                    "pi",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pi",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(create_pi_aliases),
    ]
