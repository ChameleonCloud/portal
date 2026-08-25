from django.db import migrations

UPPERCASE_VALUES = ["EMAIL", "JUSTIFICATION", "PUBLICATION", "FORM_ATTESTATION"]


def normalize_approved_with(apps, schema_editor):
    RawPublication = apps.get_model("projects", "RawPublication")
    PublicationSource = apps.get_model("projects", "PublicationSource")
    for Model in (RawPublication, PublicationSource):
        for val in UPPERCASE_VALUES:
            Model.objects.filter(approved_with=val).update(
                approved_with=val.lower()
            )


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0043_rawpublication_audit_date"),
    ]

    operations = [
        migrations.RunPython(
            normalize_approved_with,
            migrations.RunPython.noop,
        ),
    ]
