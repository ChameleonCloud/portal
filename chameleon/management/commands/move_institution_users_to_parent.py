from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from chameleon.models import Institution


class Command(BaseCommand):
    help = (
        "Move users off institutions that share their parent's website domain "
        "(e.g. Argonne labs on anl.gov) to the top-most institution owning it"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be moved without writing to the DB",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        same_domain_parent = Institution.objects.filter(
            ror_id=OuterRef("parent_ror_id"),
            website_domain=OuterRef("website_domain"),
        )
        children = (
            Institution.objects.exclude(website_domain="")
            .filter(Exists(same_domain_parent), users__isnull=False)
            .distinct()
            .order_by("website_domain", "name")
        )
        moved = 0
        for child in children:
            target = child
            while parent := Institution.objects.filter(
                ror_id=target.parent_ror_id, website_domain=child.website_domain
            ).first():
                target = parent
            links = child.users.all()
            count = links.count()
            self.stdout.write(
                f"{child} ({child.website_domain}): {count} users -> {target}"
            )
            if not dry_run:
                links.filter(user__institutions__institution=target).delete()
                links.update(institution=target)
            moved += count
        self.stdout.write(f"{'Would move' if dry_run else 'Moved'} {moved} users")
