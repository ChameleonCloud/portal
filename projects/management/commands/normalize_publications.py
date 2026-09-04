"""
Normalize publication types and/or venue assignments for approved publications.

By default both passes run. Use --types or --forums to run only one.

Venue normalization pipeline (per publication):
  1. Skip if thesis (institution names are not real venues)
  2. Preprocess arXiv paper-ID strings → "arXiv"
  3. Exact alias match in VenueSeriesAlias
  4. Heuristic alias match (normalized string)
  5. OpenAlex lookup: if no work ID stored yet, search by title; then fetch
     primary_location.source for an authoritative venue name and type
  6. AI (GPT) fallback


Type normalization: maps free-text publication_type to one of the 15 canonical
values from magpub, using BibTeX ENTRYTYPE and keyword heuristics.
"""

import json
import re
import time
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction, models

from openai import OpenAI

from projects.models import (
    Publication,
    PublicationCitation,
    VenueSeries,
    VenueSeriesAlias,
    VenueEdition,
)
from magpub.sources.openalex import OpenAlexClient
from magpub.utils import get_pub_type_from_str, how_similar

logger = logging.getLogger(__name__)

THESIS_TYPES = {"phd thesis", "ms thesis", "thesis"}

# arXiv per-paper-ID string: "arXiv preprint arXiv:2301.12345" → "arXiv"
ARXIV_PREPRINT_RE = re.compile(
    r"arXiv\s+preprint\s+arXiv:\d{4}\.\d+", re.IGNORECASE
)

# Supercomputing year-prefix: "SC24: International Conference..." → strip prefix
SC_YEAR_PREFIX_RE = re.compile(r"^SC\d{2}:\s*", re.IGNORECASE)

# AI responses that are not real venue names
AI_UNKNOWN_NAMES = {"unknown", "n/a", "none", ""}


# Minimum title-similarity to accept an OpenAlex title match
OPENALEX_TITLE_THRESHOLD = 0.85
OPENALEX_REQUEST_DELAY = 0.2

# OpenAlex source.type → VenueSeries.VenueType
OPENALEX_TYPE_MAP = {
    "journal": VenueSeries.VenueType.JOURNAL,
    "conference": VenueSeries.VenueType.CONFERENCE,
    "repository": VenueSeries.VenueType.PREPRINT_SERVER,
}

# Infer publication_type from venue_type when pub type is vague
VENUE_TO_PUB_TYPE = {
    VenueSeries.VenueType.JOURNAL: "journal article",
    VenueSeries.VenueType.CONFERENCE: "conference paper",
    VenueSeries.VenueType.WORKSHOP: "conference paper",
    VenueSeries.VenueType.SYMPOSIUM: "conference paper",
    VenueSeries.VenueType.PREPRINT_SERVER: "preprint",
}

# Types specific enough that forum-type inference should not overwrite them.
# "journal article" is NOT included: a known conference venue is more authoritative
# than a BibTeX @article entry type, which users frequently submit incorrectly.
SPECIFIC_PUB_TYPES = {
    "conference short paper",
    "conference poster",
    "conference demo",
    "ms thesis",
    "phd thesis",
    "thesis",
    "preprint",
    "software",
    "book chapter",
    "patent",
    "poster",
    "tech report",
}


class Command(BaseCommand):
    help = (
        "Normalize publication types and/or forums for approved publications. "
        "Runs both passes by default; use --types or --forums to run only one."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--types",
            action="store_true",
            default=False,
            help="Normalize publication_type values only.",
        )
        parser.add_argument(
            "--forums",
            action="store_true",
            default=False,
            help="Normalize forum/venue data only.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview changes without saving.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop forum normalization after processing N publications.",
        )

    def handle(self, *args, **opts):
        self.dry_run = opts["dry_run"]
        run_types = opts["types"]
        run_forums = opts["forums"]

        # Default: run both passes
        if not run_types and not run_forums:
            run_types = run_forums = True

        self.openalex_client = OpenAlexClient()
        self._openalex_budget_exhausted = False  # skip OpenAlex after first 429 budget error
        self.ai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE_URL,
        )

        if run_types:
            self._run_type_normalization()

        if run_forums:
            self._run_forum_normalization(limit=opts["limit"])

    # -------------------------------------------------------------------------
    # Type normalization
    # -------------------------------------------------------------------------

    def _run_type_normalization(self):
        qs = Publication.objects.filter(status=Publication.STATUS_APPROVED)
        updates = []
        for pub in qs.iterator():
            normalized = get_pub_type_from_str(pub.publication_type, pub.bibtex_source)
            if normalized != pub.publication_type:
                updates.append((pub.id, pub.publication_type, normalized))

        if not updates:
            self.stdout.write("Types: nothing to normalize.")
            return

        self.stdout.write(f"Types: {len(updates)} publication(s) to update")
        for pub_id, old, new in updates:
            self.stdout.write(f"  [{pub_id}] '{old}' → '{new}'")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("Types: dry run — no changes saved."))
            return

        with transaction.atomic():
            for pub_id, _, new in updates:
                Publication.objects.filter(id=pub_id).update(publication_type=new)

        self.stdout.write(self.style.SUCCESS(f"Types: updated {len(updates)} record(s)."))

    # -------------------------------------------------------------------------
    # Forum normalization
    # -------------------------------------------------------------------------

    def _run_forum_normalization(self, limit=None):
        qs = (
            Publication.objects.filter(
                status=Publication.STATUS_APPROVED,
                venue_edition__isnull=True,
            )
            .select_related("citation")
            .order_by("id")
        )
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Forums: processing {total} publication(s)...")

        for pub in qs.iterator():
            self._process_publication_forum(pub)

    def _process_publication_forum(self, publication):
        # 1. Skip theses — the institution name is not a real venue
        if publication.publication_type in THESIS_TYPES:
            return

        # Pick the best raw forum string by source priority + recency
        raw_source = (
            publication.raw_sources.exclude(forum__isnull=True)
            .exclude(forum__exact="")
            .annotate(
                source_rank=models.Case(
                    models.When(name="scopus", then=models.Value(0)),
                    models.When(name="semantic_scholar", then=models.Value(1)),
                    default=models.Value(2),
                    output_field=models.IntegerField(),
                )
            )
            .order_by("source_rank", "-entry_created_date")
            .first()
        )

        raw_forum = (raw_source.forum.strip() if raw_source and raw_source.forum else "")

        # 2. Preprocess known raw-string patterns before alias lookup
        if raw_forum and ARXIV_PREPRINT_RE.match(raw_forum):
            raw_forum = "arXiv"
        elif raw_forum and SC_YEAR_PREFIX_RE.match(raw_forum):
            # "SC24: International Conference for High Performance Computing..."
            # → strip prefix so alias lookup finds "Supercomputing" / "International
            #   Conference for High Performance Computing..."
            raw_forum = SC_YEAR_PREFIX_RE.sub("", raw_forum)

        # 3. Exact alias match
        if raw_forum:
            alias = (
                VenueSeriesAlias.objects.filter(alias=raw_forum)
                .select_related("series")
                .first()
            )
            if alias:
                self._attach(publication, alias.series, raw_forum, reason="exact alias")
                return

        # 4. Heuristic alias match
        if raw_forum:
            norm = self._normalize_string(raw_forum)
            alias = (
                VenueSeriesAlias.objects.filter(alias__iexact=norm)
                .select_related("series")
                .first()
            )
            if alias:
                self._attach(publication, alias.series, raw_forum, reason="heuristic alias")
                return

        # 5. OpenAlex lookup (fetch work ID if missing, then get venue)
        openalex_id = self._ensure_openalex_id(publication)
        if openalex_id:
            forum = self._forum_from_openalex_id(openalex_id, raw_forum)
            if forum:
                self._attach(publication, forum, raw_forum, reason="openalex")
                return

        # 6. AI fallback (requires a forum string to classify)
        if not raw_forum:
            return

        ai_data = self._generate_forum_metadata([raw_forum])
        if not ai_data:
            self.stdout.write(
                self.style.WARNING(
                    f"Forums: could not normalize forum for publication {publication.pk}"
                )
            )
            return

        host_series = None
        parent_name = ai_data.get("parent_name")
        if parent_name:
            host_series, _ = VenueSeries.objects.get_or_create(
                name=parent_name,
                defaults={
                    "venue_type": VenueSeries.VenueType.CONFERENCE,
                    "organization": ai_data.get("organization", VenueSeries.Organization.UNKNOWN),
                    "source": "ai",
                    "source_comment": "Host series created via AI normalization",
                },
            )

        series, created = VenueSeries.objects.get_or_create(
            name=ai_data["name"],
            defaults={
                "organization": ai_data.get("organization", VenueSeries.Organization.UNKNOWN),
                "venue_type": ai_data.get("forum_type", VenueSeries.VenueType.UNKNOWN),
                "host_series": host_series,
                "source": "ai",
                "source_comment": "Created via AI normalization",
            },
        )
        VenueSeriesAlias.objects.get_or_create(alias=raw_forum, defaults={"series": series})
        self._attach(publication, series, raw_forum, reason="ai")
        if created:
            self.stdout.write(f"  Created forum: {series.name} [{series.organization}]")

    def _ensure_openalex_id(self, publication):
        """Return a stored OpenAlex work ID, or search OpenAlex by title to get one."""
        try:
            citation = publication.citation
            if citation.openalex_source_id:
                return citation.openalex_source_id
        except PublicationCitation.DoesNotExist:
            citation = None

        # Don't attempt a new search if budget is exhausted for this run
        if self._openalex_budget_exhausted:
            return None

        if not publication.title:
            return None

        try:
            works = self.openalex_client.search_by_title(
                publication.title, year=publication.year
            )
        except Exception as exc:
            exc_str = str(exc)
            if "Insufficient budget" in exc_str or "Rate limit exceeded" in exc_str:
                self._openalex_budget_exhausted = True
                logger.warning("OpenAlex budget exhausted — skipping for remainder of run")
            else:
                logger.warning("OpenAlex search failed for pub %s: %s", publication.pk, exc)
            time.sleep(OPENALEX_REQUEST_DELAY)
            return None

        time.sleep(OPENALEX_REQUEST_DELAY)

        best_work = None
        best_score = 0.0
        for work in works:
            score = how_similar(
                publication.title.lower(), (work.get("title") or "").lower()
            )
            if score > best_score:
                best_score = score
                best_work = work

        if best_work is None or best_score < OPENALEX_TITLE_THRESHOLD:
            return None

        openalex_id = best_work.get("id", "")
        if not openalex_id:
            return None

        if not self.dry_run:
            citation, _ = PublicationCitation.objects.get_or_create(publication=publication)
            citation.openalex_source_id = openalex_id
            citation.openalex_citation_count = best_work.get("cited_by_count") or 0
            citation.save(update_fields=["openalex_source_id", "openalex_citation_count"])

            # Backfill forum string from OpenAlex if publication has none
            primary_location = best_work.get("primary_location") or {}
            source = primary_location.get("source") or {}
            venue_name = (source.get("display_name") or "").strip()
            if venue_name and not publication.forum:
                publication.forum = venue_name
                publication.save(update_fields=["forum"])

        return openalex_id

    def _forum_from_openalex_id(self, openalex_id, raw_forum):
        """Fetch primary_location.source from OpenAlex and return a VenueSeries instance."""
        try:
            work = self.openalex_client.get_work(openalex_id)
        except Exception:
            return None
        if not work:
            return None
        time.sleep(OPENALEX_REQUEST_DELAY)

        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        display_name = (source.get("display_name") or "").strip()
        source_type = source.get("type", "")

        if not display_name:
            return None

        alias = (
            VenueSeriesAlias.objects.filter(alias=display_name)
            .select_related("series")
            .first()
        )
        if alias:
            return alias.series

        venue_type = OPENALEX_TYPE_MAP.get(source_type, VenueSeries.VenueType.OTHER)
        series, created = VenueSeries.objects.get_or_create(
            name=display_name,
            defaults={
                "venue_type": venue_type,
                "organization": VenueSeries.Organization.UNKNOWN,
                "source": "openalex",
                "source_comment": f"Created from OpenAlex source type '{source_type}'",
            },
        )
        VenueSeriesAlias.objects.get_or_create(alias=display_name, defaults={"series": series})
        if raw_forum and raw_forum != display_name:
            VenueSeriesAlias.objects.get_or_create(alias=raw_forum, defaults={"series": series})
        if created:
            self.stdout.write(
                f"  Created forum from OpenAlex: {series.name} [{venue_type}]"
            )
        return series

    def _normalize_string(self, value):
        value = value.lower()
        value = re.sub(r"\W+", " ", value)
        return value.strip()

    def _generate_forum_metadata(self, raw_forums):
        prompt = "Raw forum strings:\n" + "".join(f"- {f}\n" for f in raw_forums)

        system_prompt = """
You normalize academic publication forums.

CRITICAL DEFINITIONS:
- "name" is the SHORT, CANONICAL SERIES NAME of the venue.
- "name" MUST be stable across years.
- "name" MUST NOT include year numbers, hosting organizations, locations, workshop
  titles, or phrases like "International Conference on", "Proceedings of", etc.

Examples:
- "The International Conference for High Performance Computing, Networking, Storage,
  and Analysis" → name: "Supercomputing"
- "SC24" → name: "Supercomputing"
- "XYZ Workshop at Supercomputing 2023" → name: "Supercomputing"
- "Practice and Experience in Advanced Research Computing" → name: "PEARC"
- "arXiv" or "arXiv preprint" → name: "arXiv", forum_type: "preprint_server"
- "SSRN" → name: "SSRN", forum_type: "preprint_server"

ABBREVIATIONS: If a venue has a widely used abbreviation (SC, PEARC, SIGMOD, VLDB),
ALWAYS use the abbreviation as the canonical "name".

Return EXACTLY ONE JSON OBJECT. No list, no markdown, no explanation.

JSON fields:
- name: canonical series name (string, required)
- organization: one of [acm, ieee, usenix, springer, elsevier, other, unknown]
- forum_type: one of [conference, journal, workshop, symposium, preprint_server, other, unknown]
- country: host country or empty string

Rules:
- For workshops: "name" is the WORKSHOP SERIES NAME; "forum_type" is "workshop";
  include "parent_name" as the canonical parent venue name (if known).
- For arXiv, bioRxiv, SSRN, or similar: "forum_type" is "preprint_server".
- Prefer abbreviation over expanded form.
- Use null or "unknown" when unsure.

Respond with ONLY valid JSON.
"""

        try:
            response = self.ai_client.chat.completions.create(
                model=settings.OPENAI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            logger.warning("AI forum classification failed: %s", exc)
            return None

        content = response.choices[0].message.content.strip()
        try:
            if content.startswith("```"):
                content = "\n".join(content.split("\n")[1:-1])
            data = json.loads(content)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid AI JSON response"))
            self.stdout.write(content)
            return None

        name = (data.get("name") or "").strip()
        if not name or name.lower() in AI_UNKNOWN_NAMES:
            return None

        return {
            "name": name[:512],
            "organization": data.get("organization", "unknown"),
            "forum_type": data.get("forum_type", "unknown"),
            "country": data.get("country", "") or "",
            "parent_name": (data.get("parent_name") or "").strip() or None,
        }

    @transaction.atomic
    def _attach(self, publication, series, raw_forum, reason):
        if self.dry_run:
            self.stdout.write(
                f"  [DRY-RUN] pub {publication.pk} → {series} ({reason})"
            )
            return

        if not publication.year:
            self.stdout.write(
                self.style.WARNING(
                    f"Forums: skipping pub {publication.pk} — no year set"
                )
            )
            return

        edition, _ = VenueEdition.objects.get_or_create(
            series=series, year=publication.year
        )
        publication.venue_edition = edition
        fields = ["venue_edition"]

        if publication.publication_type not in SPECIFIC_PUB_TYPES:
            inferred = VENUE_TO_PUB_TYPE.get(series.venue_type)
            if inferred:
                publication.publication_type = inferred
                fields.append("publication_type")

        publication.save(update_fields=fields)
        type_note = (
            f"; inferred type '{publication.publication_type}'"
            if "publication_type" in fields
            else ""
        )
        self.stdout.write(f"  pub {publication.pk} → {series} ({reason}){type_note}")
