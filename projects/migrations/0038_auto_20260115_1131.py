from django.db import migrations


def merge_forums(apps, schema_editor):
    Forum = apps.get_model("projects", "Forum")
    Publication = apps.get_model("projects", "Publication")

    # Iterate over distinct forum names
    names = (
        Forum.objects
        .values_list("name", flat=True)
        .distinct()
    )

    for name in names:
        forums = list(Forum.objects.filter(name=name).order_by("id"))

        if len(forums) <= 1:
            continue

        canonical = forums[0]
        duplicates = forums[1:]

        # Repoint publications
        Publication.objects.filter(
            normalized_forum__in=duplicates
        ).update(normalized_forum=canonical)

        # Delete duplicate forums
        for f in duplicates:
            f.delete()

def null_years(apps, schema_editor):
    Forum = apps.get_model("projects", "Forum")
    Forum.objects.update(year=None)


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0037_alter_publication_project_and_more"),
    ]

    operations = [
        migrations.RunPython(merge_forums),
        migrations.RunPython(null_years),
    ]
