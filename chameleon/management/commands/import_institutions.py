"""
Import canonical institution data from ACE Carnegie Classification and ROR data sources.

Usage:
    manage.py import_institutions --carnegie-file ace-institutional-classifications.csv
    manage.py import_institutions --ror-file v2.12-2026-08-25-ror-data.csv
    manage.py import_institutions --carnegie-file ace-*.csv --ror-file ror-data.csv

Data sources:
    ACE Carnegie Classification: https://carnegieclassifications.acenet.edu/
    ROR data dump (CSV):         https://zenodo.org/records/22099990
"""

import csv
import logging
import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from chameleon.models import Institution, InstitutionAlias

logger = logging.getLogger(__name__)

BATCH_SIZE = 500

# ACE Research Activity Designation prefix → (carnegie_classification, institution_type)
RESEARCH_DESIGNATION_MAP = {
    "research 1": ("R1", Institution.InstitutionType.R1),
    "research 2": ("R2", Institution.InstitutionType.R2),
    "research colleges and universities": ("Research", Institution.InstitutionType.R2),
}

# ACE control field → Institution.Control value
CONTROL_MAP = {
    "public": Institution.Control.PUBLIC,
    "private not-for-profit": Institution.Control.PRIVATE_NONPROFIT,
    "private for-profit": Institution.Control.PRIVATE_FORPROFIT,
}

# ROR types (lowercase) → institution_type
ROR_TYPE_MAP = {
    "education": Institution.InstitutionType.OTHER,
    "company": Institution.InstitutionType.INDUSTRY,
    "government": Institution.InstitutionType.GOVERNMENT,
    "nonprofit": Institution.InstitutionType.NONPROFIT,
    "healthcare": Institution.InstitutionType.NONPROFIT,
    "facility": Institution.InstitutionType.OTHER,
    "archive": Institution.InstitutionType.OTHER,
    "funder": Institution.InstitutionType.NONPROFIT,
    "other": Institution.InstitutionType.OTHER,
}


def _extract_domain(url):
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        host = urlparse(url).netloc.lower()
        return re.sub(r"^www\.", "", host)
    except Exception:
        return ""


def _parse_ror_name_field(raw):
    """
    ROR CSV name fields use semicolon-separated 'lang_code: value' entries.
    Returns a list of clean strings with the lang prefix stripped.
    """
    if not raw:
        return []
    results = []
    for entry in raw.split(";"):
        entry = entry.strip()
        if ": " in entry:
            entry = entry.split(": ", 1)[1].strip()
        if entry:
            results.append(entry)
    return results


def _parse_parent_ror_id(raw):
    """Extract parent ROR ID from ROR relationships column value."""
    if not raw:
        return ""
    for segment in re.split(r";\s*(?=\w+:)", raw):
        segment = segment.strip()
        if segment.lower().startswith("parent:"):
            first_url = segment.split(":", 1)[1].strip().split(",")[0].strip()
            return first_url.replace("https://ror.org/", "").strip()
    return ""


def _add_alias(institution, alias_text):
    alias_text = alias_text.strip()[:500]
    if alias_text and alias_text.lower() != institution.name.lower():
        InstitutionAlias.objects.get_or_create(
            institution=institution, alias=alias_text
        )


def _flush_batch(rows, process_fn, counters):
    with transaction.atomic():
        for row in rows:
            c, u, s = process_fn(row)
            counters[0] += c
            counters[1] += u
            counters[2] += s


class Command(BaseCommand):
    help = "Import canonical institution data from ACE Carnegie Classification and/or ROR CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--carnegie-file",
            metavar="ace-institutional-classifications.csv",
            help="Path to ACE Carnegie Classification CSV file",
        )
        parser.add_argument(
            "--ror-file",
            metavar="ror-data.csv",
            help="Path to ROR data dump CSV file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created/updated without writing to the DB",
        )

    def handle(self, *args, **options):
        if not options["carnegie_file"] and not options["ror_file"]:
            raise CommandError("Provide at least --carnegie-file or --ror-file")

        self.dry_run = options["dry_run"]
        if self.dry_run:
            self.stdout.write("DRY RUN — no changes will be written")

        if options["carnegie_file"]:
            self._import_carnegie(options["carnegie_file"])

        if options["ror_file"]:
            self._import_ror(options["ror_file"])

    # ------------------------------------------------------------------
    # Carnegie / ACE
    # ------------------------------------------------------------------

    def _import_carnegie(self, path):
        self.stdout.write(f"Importing ACE Carnegie Classification from {path} ...")
        counters = [0, 0, 0]  # created, updated, skipped
        batch = []

        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if self.dry_run:
                    c, u, s = self._process_carnegie_row(row)
                    counters[0] += c
                    counters[1] += u
                    counters[2] += s
                else:
                    batch.append(row)
                    if len(batch) >= BATCH_SIZE:
                        _flush_batch(batch, self._process_carnegie_row, counters)
                        batch = []

        if batch:
            _flush_batch(batch, self._process_carnegie_row, counters)

        self.stdout.write(
            f"Carnegie done: {counters[0]} created, {counters[1]} updated, {counters[2]} skipped"
        )

    def _process_carnegie_row(self, row):
        unitid = row.get("unitid", "").strip()
        name = row.get("name", "").strip()
        if not name:
            return 0, 0, 1

        state = row.get("state", "").strip()
        city = row.get("city", "").strip()
        control_raw = row.get("control", "").strip().lower()
        classification = row.get("Institutional Classification", "").strip()
        research_designation = row.get("Research Activity Designation", "").strip()
        carnegie_size = row.get("Size", "").strip()

        carnegie_label = ""
        institution_type = Institution.InstitutionType.OTHER
        rd_lower = research_designation.lower()
        for key, (label, itype) in RESEARCH_DESIGNATION_MAP.items():
            if rd_lower.startswith(key):
                carnegie_label = label
                institution_type = itype
                break

        if not carnegie_label:
            carnegie_label = classification
            if "associate" in classification.lower():
                institution_type = Institution.InstitutionType.COMMUNITY_COLLEGE

        control = CONTROL_MAP.get(control_raw, "")

        if self.dry_run:
            self.stdout.write(f"  Carnegie {unitid}: {name} [{carnegie_label}] {state}")
            return 1, 0, 0

        defaults = dict(
            name=name,
            state=state,
            city=city,
            carnegie_classification=carnegie_label,
            carnegie_full_classification=classification,
            carnegie_size=carnegie_size,
            institution_type=institution_type,
            control=control,
            country="US",
            source=Institution.Source.CANONICAL,
        )

        if unitid:
            # Prefer matching by unitid (already imported), then fall back to
            # matching the legacy seeded record by name so we update in place
            # rather than creating a duplicate.
            inst = Institution.objects.filter(ipeds_unitid=unitid).first()
            if inst is None:
                inst = Institution.objects.filter(
                    name__iexact=name, ipeds_unitid__isnull=True
                ).first()
            if inst is not None:
                for k, v in defaults.items():
                    setattr(inst, k, v)
                inst.ipeds_unitid = unitid
                inst.save()
                was_created = False
            else:
                inst = Institution.objects.create(ipeds_unitid=unitid, **defaults)
                was_created = True
        else:
            inst, was_created = Institution.objects.update_or_create(
                name=name, country="US", defaults=defaults
            )

        _add_alias(inst, name)
        # Add alias without leading "The " so "University of X" matches "The University of X"
        if name.lower().startswith("the "):
            _add_alias(inst, name[4:])
        return (1, 0, 0) if was_created else (0, 1, 0)

    # ------------------------------------------------------------------
    # ROR
    # ------------------------------------------------------------------

    def _import_ror(self, path):
        self.stdout.write(f"Importing ROR from {path} ...")
        counters = [0, 0, 0]
        batch = []

        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if self.dry_run:
                    c, u, s = self._process_ror_row(row)
                    counters[0] += c
                    counters[1] += u
                    counters[2] += s
                else:
                    batch.append(row)
                    if len(batch) >= BATCH_SIZE:
                        _flush_batch(batch, self._process_ror_row, counters)
                        batch = []

        if batch:
            _flush_batch(batch, self._process_ror_row, counters)

        self.stdout.write(
            f"ROR done: {counters[0]} created, {counters[1]} updated, {counters[2]} skipped"
        )

    def _process_ror_row(self, row):
        if row.get("status", "").strip().lower() != "active":
            return 0, 0, 1

        ror_id = row.get("id", "").replace("https://ror.org/", "").strip()
        display_name = row.get("names.types.ror_display", "").strip()
        if not ror_id or not display_name:
            return 0, 0, 1

        country = row.get("locations.geonames_details.country_code", "").strip()
        city = row.get("locations.geonames_details.name", "").strip()
        lat_raw = row.get("locations.geonames_details.lat", "").strip()
        lng_raw = row.get("locations.geonames_details.lng", "").strip()
        latitude = float(lat_raw) if lat_raw else None
        longitude = float(lng_raw) if lng_raw else None
        parent_ror_id = _parse_parent_ror_id(row.get("relationships", ""))

        # Prefer explicit ROR domains list (reliable for email matching) over URL extraction
        ror_domains_raw = row.get("domains", "").strip()
        if ror_domains_raw:
            domain = ror_domains_raw.split(";")[0].strip().lower()
        else:
            domain = _extract_domain(row.get("links.type.website", ""))

        raw_types = row.get("types", "")
        types = [t.strip().lower() for t in raw_types.split(";") if t.strip()]
        institution_type = Institution.InstitutionType.OTHER
        for t in types:
            if t in ROR_TYPE_MAP:
                institution_type = ROR_TYPE_MAP[t]
                break

        aliases = _parse_ror_name_field(row.get("names.types.alias", ""))
        acronyms = _parse_ror_name_field(row.get("names.types.acronym", ""))
        labels = _parse_ror_name_field(row.get("names.types.label", ""))

        if self.dry_run:
            self.stdout.write(
                f"  ROR {ror_id}: {display_name} [{institution_type}] {country}"
            )
            return 1, 0, 0

        # Already imported via ROR id — refresh domain/location and add any new aliases/labels
        existing_by_ror = Institution.objects.filter(ror_id=ror_id).first()
        if existing_by_ror:
            changed = False
            if domain and existing_by_ror.website_domain != domain:
                existing_by_ror.website_domain = domain
                changed = True
            if existing_by_ror.institution_type == Institution.InstitutionType.UNKNOWN:
                existing_by_ror.institution_type = institution_type
                changed = True
            if city and not existing_by_ror.city:
                existing_by_ror.city = city
                changed = True
            if latitude is not None and existing_by_ror.latitude is None:
                existing_by_ror.latitude = latitude
                existing_by_ror.longitude = longitude
                changed = True
            if parent_ror_id and not existing_by_ror.parent_ror_id:
                existing_by_ror.parent_ror_id = parent_ror_id
                changed = True
            if changed:
                existing_by_ror.save()
            for alias in aliases + acronyms + labels:
                _add_alias(existing_by_ror, alias)
            return (0, 1, 0) if changed else (0, 0, 1)

        # Carnegie record with same name — backfill ror_id + domain
        existing_by_name = Institution.objects.filter(
            name__iexact=display_name, ipeds_unitid__isnull=False
        ).first()
        if existing_by_name and not existing_by_name.ror_id:
            existing_by_name.ror_id = ror_id
            if domain:
                existing_by_name.website_domain = domain
            existing_by_name.save()
            return 0, 1, 0

        # New record
        inst, was_created = Institution.objects.update_or_create(
            ror_id=ror_id,
            defaults=dict(
                name=display_name,
                institution_type=institution_type,
                country=country,
                city=city,
                latitude=latitude,
                longitude=longitude,
                parent_ror_id=parent_ror_id,
                website_domain=domain,
                source=Institution.Source.CANONICAL,
            ),
        )
        for alias in aliases + acronyms + labels:
            _add_alias(inst, alias)

        return (1, 0, 0) if was_created else (0, 1, 0)
