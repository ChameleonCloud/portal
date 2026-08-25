"""
Management command to clean up legacy RawPublication records that have no
chameleon_publications or publication_queries M2M links (old citation-tracking
entries that predate the current source-linking pattern).

Tiers (mutually exclusive per record):
  same-source   -- another raw pub on the same publication, same source name,
                   with proper M2M links exists
  diff-source   -- no same-source replacement, but a different source type on
                   the same publication does have M2M links
  no-rep        -- no M2M-linked raw pub exists anywhere on the publication

Usage examples:

  # Summary only (default)
  ./manage.py cleanup_empty_raw_publications
  ./manage.py cleanup_empty_raw_publications --null-source-id

  # Inspect records in one tier
  ./manage.py cleanup_empty_raw_publications --inspect same-source
  ./manage.py cleanup_empty_raw_publications --inspect diff-source --source scopus --null-source-id

  # Delete a tier (requires --yes)
  ./manage.py cleanup_empty_raw_publications --delete same-source --yes
  ./manage.py cleanup_empty_raw_publications --delete no-rep --null-source-id --yes

  # Limit to specific source(s)
  ./manage.py cleanup_empty_raw_publications --delete same-source --source scopus --source semantic_scholar --yes
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from projects.models import RawPublication

ALGORITHMIC_SOURCES = [
    RawPublication.SCOPUS,
    RawPublication.SEMANTIC_SCHOLAR,
    RawPublication.GOOGLE_SCHOLAR,
    RawPublication.SCIENCE_DIRECT,
    RawPublication.OPENALEX,
]

TIERS = ["same-source", "diff-source", "no-rep"]
INSPECT_LIMIT = 20

_HAS_ANY_LINKED = Q(
    publication__raw_sources__chameleon_publications__isnull=False
) | Q(publication__raw_sources__publication_queries__isnull=False)


def _base_qs(sources, null_source_id=False, include_attributed=False, before=None):
    # ALL operations in this command are scoped to this queryset.
    # Only records with BOTH M2M fields null are ever touched.
    qs = RawPublication.objects.filter(
        chameleon_publications__isnull=True,
        publication_queries__isnull=True,
        name__in=sources,
    )
    if not include_attributed:
        qs = qs.filter(cites_chameleon=False, acknowledges_chameleon=False)
    if null_source_id:
        qs = qs.filter(source_id__isnull=True)
    if before:
        qs = qs.filter(entry_created_date__lt=before)
    return qs


def _same_source_ids(sources, null_source_id=False, include_attributed=False, before=None):
    """
    Return PKs of empty raw pubs that have a same-source replacement.
    Evaluated in Python because the per-row join on name can't be expressed
    cleanly in the ORM without a self-join.
    """
    result = []
    for rp in _base_qs(sources, null_source_id, include_attributed, before).select_related("publication"):
        has_replacement = (
            RawPublication.objects.filter(publication=rp.publication, name=rp.name)
            .exclude(
                chameleon_publications__isnull=True,
                publication_queries__isnull=True,
            )
            .exists()
        )
        if has_replacement:
            result.append(rp.pk)
    return result


def _tier_qs(tier, sources, same_ids, null_source_id=False, include_attributed=False, before=None):
    base = _base_qs(sources, null_source_id, include_attributed, before)
    if tier == "same-source":
        return base.filter(id__in=same_ids)
    elif tier == "diff-source":
        return base.filter(_HAS_ANY_LINKED).exclude(id__in=same_ids).distinct()
    else:  # no-rep
        any_rep_ids = base.filter(_HAS_ANY_LINKED).values_list("id", flat=True)
        return base.exclude(id__in=any_rep_ids).distinct()


class Command(BaseCommand):
    help = "Inspect and optionally delete legacy empty RawPublication records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inspect",
            choices=TIERS,
            metavar="TIER",
            help=f"Print a sample of records in a tier ({', '.join(TIERS)}).",
        )
        parser.add_argument(
            "--delete",
            choices=TIERS,
            metavar="TIER",
            help="Delete all records in a tier (requires --yes).",
        )
        parser.add_argument(
            "--source",
            action="append",
            dest="sources",
            choices=ALGORITHMIC_SOURCES,
            metavar="SOURCE",
            help="Limit to one or more sources (repeatable). Default: all algorithmic sources.",
        )
        parser.add_argument(
            "--null-source-id",
            action="store_true",
            default=False,
            help="Only consider records where source_id is null.",
        )
        parser.add_argument(
            "--include-attributed",
            action="store_true",
            default=False,
            help="Include records where cites_chameleon or acknowledges_chameleon is True (excluded by default).",
        )
        parser.add_argument(
            "--before",
            metavar="DATE",
            help="Only consider records with entry_created_date before DATE (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=INSPECT_LIMIT,
            help=f"Max rows to print with --inspect (default {INSPECT_LIMIT}).",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion (required with --delete).",
        )

    def handle(self, *args, **opts):
        sources = opts["sources"] or ALGORITHMIC_SOURCES
        inspect_tier = opts["inspect"]
        delete_tier = opts["delete"]
        limit = opts["limit"]
        yes = opts["yes"]
        null_source_id = opts["null_source_id"]
        include_attributed = opts["include_attributed"]
        before = self._parse_before(opts["before"])

        if not inspect_tier and not delete_tier:
            self._print_summary(sources, null_source_id, include_attributed, before)
            return

        # Pre-compute same-source IDs once if either tier needs them
        same_ids = (
            _same_source_ids(sources, null_source_id, include_attributed, before)
            if (inspect_tier in ("same-source", "diff-source"))
            or (delete_tier in ("same-source", "diff-source"))
            else []
        )

        if inspect_tier:
            self._inspect(inspect_tier, sources, limit, same_ids, null_source_id, include_attributed, before)

        if delete_tier:
            if not yes:
                self.stdout.write(self.style.ERROR("Add --yes to confirm deletion."))
                return
            self._delete(delete_tier, sources, same_ids, null_source_id, include_attributed, before)

    def _parse_before(self, value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            raise CommandError(f"--before must be YYYY-MM-DD, got: {value!r}")

    def _print_summary(self, sources, null_source_id, include_attributed, before):
        self.stdout.write(f"Sources: {', '.join(sources)}\n")
        if null_source_id:
            self.stdout.write("Filter:  source_id is null\n")
        if before:
            self.stdout.write(f"Filter:  entry_created_date < {before}\n")
        if not include_attributed:
            self.stdout.write(
                "Filter:  cites_chameleon=False, acknowledges_chameleon=False "
                "(use --include-attributed to override)\n"
            )
        total = _base_qs(sources, null_source_id, include_attributed, before).count()
        self.stdout.write(f"Total matching records: {total}\n")

        same_ids = _same_source_ids(sources, null_source_id, include_attributed, before)
        base = _base_qs(sources, null_source_id, include_attributed, before)

        same_count = len(same_ids)
        diff_count = (
            base.filter(_HAS_ANY_LINKED).exclude(id__in=same_ids).distinct().count()
        )
        no_rep_count = (
            base.exclude(
                id__in=base.filter(_HAS_ANY_LINKED).values_list("id", flat=True)
            )
            .distinct()
            .count()
        )

        self.stdout.write(
            f"  same-source replacement : {same_count:>6}  (--delete same-source)\n"
            f"  diff-source replacement : {diff_count:>6}  (--delete diff-source)\n"
            f"  no replacement          : {no_rep_count:>6}  (--delete no-rep)\n"
        )
        self.stdout.write(
            "Run with --inspect <tier> to examine records, "
            "--delete <tier> --yes to remove them."
        )

    def _inspect(self, tier, sources, limit, same_ids, null_source_id, include_attributed, before):
        qs = _tier_qs(tier, sources, same_ids, null_source_id, include_attributed, before)
        total = qs.count()
        self.stdout.write(f"\nTier '{tier}': {total} records (showing up to {limit})\n")
        self.stdout.write(
            f"{'ID':>7}  {'source':<18}  {'created':<12}  {'pub_id':>7}  {'pub_status':<25}  title"
        )
        self.stdout.write("-" * 120)

        for rp in qs.select_related("publication")[:limit]:
            pub = rp.publication
            title = (pub.title or "")[:50]
            self.stdout.write(
                f"{rp.id:>7}  {rp.name:<18}  {str(rp.entry_created_date):<12}  "
                f"{pub.id:>7}  {pub.status:<25}  {title}"
            )

        descriptions = {
            "same-source": (
                "Each of these has another raw pub of the same source "
                "with chameleon_publications or publication_queries set."
            ),
            "diff-source": (
                "No same-source replacement, but the publication has at least "
                "one M2M-linked raw pub from a different source."
            ),
            "no-rep": "No M2M-linked raw pub exists anywhere on these publications.",
        }
        self.stdout.write(f"\n  {descriptions[tier]}")

    def _delete(self, tier, sources, same_ids, null_source_id, include_attributed, before):
        qs = _tier_qs(tier, sources, same_ids, null_source_id, include_attributed, before)
        ids = list(qs.values_list("id", flat=True))
        if not ids:
            self.stdout.write(self.style.SUCCESS("Nothing to delete."))
            return
        deleted, _ = RawPublication.objects.filter(id__in=ids).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} RawPublication records (tier: {tier})."
            )
        )
