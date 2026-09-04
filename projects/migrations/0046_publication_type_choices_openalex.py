from django.db import migrations, models


def normalize_publication_types(apps, schema_editor):
    Publication = apps.get_model("projects", "Publication")
    try:
        from magpub.utils import get_pub_type_from_str
    except ImportError:
        return

    valid_values = {
        "preprint", "journal article", "conference paper", "conference short paper",
        "conference poster", "conference demo", "tech report", "ms thesis",
        "phd thesis", "thesis", "software", "book chapter", "patent", "poster", "other",
    }

    for pub in Publication.objects.iterator():
        normalized = get_pub_type_from_str(pub.publication_type, pub.bibtex_source)
        if normalized not in valid_values:
            normalized = "other"
        if normalized != pub.publication_type:
            pub.publication_type = normalized
            pub.save(update_fields=["publication_type"])


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0045_alter_invitation_user_accepted_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_publication_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="publication",
            name="publication_type",
            field=models.CharField(
                max_length=50,
                choices=[
                    ("preprint", "Preprint"),
                    ("journal article", "Journal Article"),
                    ("conference paper", "Conference Paper"),
                    ("conference short paper", "Conference Short Paper"),
                    ("conference poster", "Conference Poster"),
                    ("conference demo", "Conference Demo"),
                    ("tech report", "Tech Report"),
                    ("ms thesis", "MS Thesis"),
                    ("phd thesis", "PhD Thesis"),
                    ("thesis", "Thesis"),
                    ("software", "Software"),
                    ("book chapter", "Book Chapter"),
                    ("patent", "Patent"),
                    ("poster", "Poster"),
                    ("other", "Other"),
                ],
                default="other",
            ),
        ),
        migrations.AlterField(
            model_name="forum",
            name="forum_type",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("conference", "Conference"),
                    ("journal", "Journal"),
                    ("workshop", "Workshop"),
                    ("symposium", "Symposium"),
                    ("preprint_server", "Preprint Server"),
                    ("other", "Other"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
            ),
        ),
        migrations.AddField(
            model_name="publicationcitation",
            name="openalex_citation_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="publicationcitation",
            name="openalex_source_id",
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
