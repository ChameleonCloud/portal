# yourapp/management/commands/normalize_pubtypes.py

from django.core.management.base import BaseCommand
from django.db import transaction
from projects.models import Publication, RawPublication  # change to correct app

PREPRINT = "preprint"
JOURNAL_ARTICLE = "journal article"
CONFERENCE_PAPER = "conference paper"
CONFERENCE_SHORT_PAPER = "conference short paper"
CONFERENCE_POSTER = "conference poster"
CONFERENCE_DEMO = "conference demo"
TECH_REPORT = "tech report"
MS_THESIS = "ms thesis"
PHD_THESIS = "phd thesis"
THESIS = "thesis"
SOFTWARE = "software"
BOOK_CHAPTER = "book chapter"
PATENT = "patent"
OTHER = "other"

EXACT_MAP = {
    # Preprints
    "pre-print": PREPRINT,
    "preprint": PREPRINT,

    # Journal article
    "journal article": JOURNAL_ARTICLE,
    "research article": JOURNAL_ARTICLE,
    "article": JOURNAL_ARTICLE,

    # Conference categories
    "conference full paper": CONFERENCE_PAPER,
    "conference short paper": CONFERENCE_SHORT_PAPER,
    "conference poster": CONFERENCE_POSTER,
    "conference demostration": CONFERENCE_DEMO,
    "conference demo": CONFERENCE_DEMO,
    "conference paper": CONFERENCE_PAPER,
    "conference": CONFERENCE_PAPER,
    "inproceedings": CONFERENCE_PAPER,
    "poster": CONFERENCE_POSTER,

    # Tech report
    "tech report": TECH_REPORT,
    "techreport": TECH_REPORT,

    # Thesis categories
    "ms thesis": MS_THESIS,
    "phd thesis": PHD_THESIS,
    "dissertation": PHD_THESIS,
    "thesis": THESIS,

    # Software/code
    "github": SOFTWARE,
    "software": SOFTWARE,

    # Books
    "book chapter": BOOK_CHAPTER,

    # Patent
    "patent": PATENT,

    # Everything else (handled by fallbacks)
    "misc": OTHER,
    "other": OTHER,
}

BIBTEX_RULES = [
    # Conference
    (("@inproceedings", "@conference", "@proceedings",
    "@incollection", "@workshop"), CONFERENCE_PAPER),

    # Thesis
    (("@phdthesis",), PHD_THESIS),
    (("@mastersthesis",), MS_THESIS),
    (("@thesis",), THESIS),

    # Journal
    (("@article",), JOURNAL_ARTICLE),

    # Books & chapters
    (("@book", "@inbook", "@booklet"), BOOK_CHAPTER),

    # Reports
    (("@techreport", "@report"), TECH_REPORT),

    # Software / code
    (("@software", "@code"), SOFTWARE),

    # Dataset
    (("@dataset", "@data"), OTHER),

    # Manual
    (("@manual",), OTHER),

    # Patent
    (("@patent",), PATENT),

    # Online / webpage
    (("@online", "@webpage"), OTHER),

    # Unpublished
    (("@unpublished",), OTHER),

    # Misc
    (("@misc",), OTHER),
]


def fallback_category(value: str) -> str:
    """Rule-based normalization if value not in EXACT_MAP."""

    if "pre" in value and "print" in value:
        return PREPRINT

    if "conference" in value or "proceed" in value:
        return CONFERENCE_PAPER

    if "poster" in value:
        return CONFERENCE_POSTER

    if "thesis" in value:
        if "phd" in value:
            return PHD_THESIS
        if "ms" in value or "master" in value:
            return MS_THESIS
        return THESIS

    if "journal" in value:
        return JOURNAL_ARTICLE

    if "tech" in value and "report" in value:
        return TECH_REPORT

    return None


class Command(BaseCommand):
    help = "Normalize RawPublication.publication_type into clear categories."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true",
                            help="Apply changes.")
        parser.add_argument("--dry-run", action="store_true",
                            default=True,
                            help="Only display changes (default).")
        parser.add_argument("--no-dry-run", action="store_false",
                            dest="dry_run",
                            help="Actually apply changes (requires --yes).")

    def normalize(self, pub: RawPublication) -> str:
        val = pub.publication_type.strip().lower()

        if val in EXACT_MAP:
            return EXACT_MAP[val]

        res = fallback_category(val)

        # If fallback not found, check bibtex source rules
        src = (pub.bibtex_source or "").strip().lower()
        if not res and src.startswith("@"):
            for prefixes, result_type in BIBTEX_RULES:
                if any(src.startswith(prefix) for prefix in prefixes):
                    return result_type

        return OTHER

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
