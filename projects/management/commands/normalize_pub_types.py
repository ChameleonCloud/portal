# yourapp/management/commands/normalize_pubtypes.py

from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Publication, RawPublication
from magpub.utils import get_pub_type_from_str


class Command(BaseCommand):
    help = "Normalize RawPublication.publication_type into clear categories."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Apply changes.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Only display changes (default).",
        )
        parser.add_argument(
            "--no-dry-run",
            action="store_false",
            dest="dry_run",
            help="Actually apply changes (requires --yes).",
        )

    def normalize(self, pub: RawPublication) -> str:
        return get_pub_type_from_str(pub.publication_type, pub.bibtex_source)

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        yes = opts["yes"]

        qs = Publication.objects.all()

        updates = []

        for pub in qs:
            original = pub.publication_type
            normalized = self.normalize(pub)
            if normalized != original:
                updates.append((pub.id, original, normalized))

        if not updates:
            self.stdout.write(self.style.SUCCESS("Nothing to normalize."))
            return

        self.stdout.write("Proposed updates:\n")
        for pub_id, old, new in updates:
            self.stdout.write(f"  ID {pub_id}: '{old}' → '{new}'")

        if dry:
            self.stdout.write(self.style.WARNING("Dry run: no changes applied."))
            self.stdout.write("Use: --no-dry-run --yes")
            return

        if not yes:
            self.stdout.write(self.style.ERROR("Add --yes to apply changes."))
            return

        with transaction.atomic():
            for pub_id, _, new in updates:
                Publication.objects.filter(id=pub_id).update(publication_type=new)

        self.stdout.write(self.style.SUCCESS(f"Updated {len(updates)} records."))
