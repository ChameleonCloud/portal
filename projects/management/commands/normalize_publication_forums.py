# publications/management/commands/normalize_forums.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction, models
import json
import re

from openai import OpenAI

from projects.models import Publication, Forum, ForumAlias


class Command(BaseCommand):
    help = "Normalize user-supplied publication forums into Forum/ForumAlias models"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        if not self.dry_run and OpenAI is None:
            self.stdout.write(self.style.ERROR("openai package not installed"))
            return

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE_URL,
        )

        publications = Publication.objects.filter(
            status=Publication.STATUS_APPROVED, normalized_forum__isnull=True
        )

        self.stdout.write(f"Processing {publications.count()} publications")

        for pub in publications.iterator():
            self.process_publication(pub)

    def process_publication(self, publication):
        # Pick ONE best raw forum based on source priority + recency
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

        if not raw_source or not raw_source.forum:
            return

        raw_forum = raw_source.forum.strip()
        raw_forums = [raw_forum]

        # 1. Exact alias match
        alias = (
            ForumAlias.objects.filter(alias=raw_forum).select_related("forum").first()
        )
        if alias:
            self.attach(publication, alias.forum, reason="exact alias")
            return

        # 2. Heuristic alias match
        normalized = self.normalize_string(raw_forum)
        alias = ForumAlias.objects.filter(alias__iexact=normalized).first()
        if alias:
            self.attach(publication, alias.forum, reason="heuristic alias")
            return

        # 3. AI normalization (single forum)
        ai_data = self.generate_forum_metadata(raw_forums)
        if not ai_data:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not normalize forum for publication {publication.pk}"
                )
            )
            return

        # Handle parent forum if returned by AI
        parent_forum = None
        parent_name = ai_data.get("parent_name")
        if parent_name:
            parent_forum, _ = Forum.objects.get_or_create(
                name=parent_name,
                defaults={
                    "forum_type": "conference",  # assume parent is a conference
                    "organization": ai_data.get("organization", "unknown"),
                    "country": ai_data.get("country", ""),
                    "source": "ai",
                    "source_comment": "Parent venue created via AI normalization",
                },
            )

        # Create the main forum (workshop or conference)
        forum, created = Forum.objects.get_or_create(
            name=ai_data["name"],
            defaults={
                "organization": ai_data.get("organization", "unknown"),
                "forum_type": ai_data.get("forum_type", "unknown"),
                "country": ai_data.get("country", ""),
                "parent_forum": parent_forum,  # link to parent if exists
                "source": "ai",
                "source_comment": "Created via AI normalization",
            },
        )

        # Create alias for the raw forum string
        ForumAlias.objects.get_or_create(
            forum=forum,
            alias=raw_forums[0],
        )

        # Attach the publication
        self.attach(publication, forum, reason="openai generated")

        if created:
            self.stdout.write(f"Created forum: {forum.name} [{forum.organization}]")

    def normalize_string(self, value):
        value = value.lower()
        value = re.sub(r"\W+", " ", value)
        return value.strip()

    def generate_forum_metadata(self, raw_forums):
        prompt = "Raw forum strings:\n"
        for f in raw_forums:
            prompt += f"- {f}\n"

        system_prompt = """
You normalize academic publication forums.

CRITICAL DEFINITIONS:
- "name" is the SHORT, CANONICAL SERIES NAME of the venue.
- "name" MUST be stable across years.
- "name" MUST NOT include:
  - year numbers
  - hosting organizations (ACM, IEEE, etc.)
  - locations
  - workshop titles
  - phrases like "International Conference on", "Proceedings of", etc.

Examples:
- "The International Conference for High Performance Computing, Networking, Storage, and Analysis"
  → name: "Supercomputing"
- "SC24" → name: "Supercomputing"
- "XYZ Workshop at Supercomputing 2023"
  → name: "Supercomputing"
- "Practice and Experience in Advanced Research Computing"
  → name: "PEARC"

ABBREVIATIONS:
- If a venue has a widely used abbreviation (e.g. SC, PEARC, SIGMOD, VLDB),
  ALWAYS use the abbreviation as the canonical "name".
- Do NOT alternate between abbreviation and expanded form.

Return EXACTLY ONE JSON OBJECT.
Do NOT return a list.
Do NOT include markdown or explanations.

JSON fields:
- name: canonical series name (string, required)
- organization: one of [acm, ieee, usenix, springer, elsevier, other, unknown]
- forum_type: one of [conference, journal, workshop, symposium, other, unknown]
- country: host country or empty string

Rules:
- If the input refers to a workshop:
  - "name" MUST be the WORKSHOP SERIES NAME (stable across years)
  - "forum_type" MUST be "workshop"
  - Include "parent_name" as the canonical parent venue (if known)
- Prefer abbreviation over expanded form when one is commonly used.
- Do NOT invent data; use null or "unknown" when unsure.

Respond with ONLY valid JSON.
"""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content.strip()
        try:
            if content.startswith("```"):
                content = "\n".join(content.split("\n")[1:-1])
            data = json.loads(content)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid AI JSON"))
            self.stdout.write(content)
            return None

        print(data)
        name = (data.get("name") or "").strip()
        if not name:
            return None

        return {
            "name": name[:512],
            "organization": data.get("organization", "unknown"),
            "forum_type": data.get("forum_type", "unknown"),
            "country": data.get("country", ""),
        }

    @transaction.atomic
    def attach(self, publication, forum, reason):
        if self.dry_run:
            self.stdout.write(
                f"[DRY-RUN] Would attach publication {publication.pk} → {forum} ({reason})"
            )
            return

        publication.normalized_forum = forum
        publication.save(update_fields=["normalized_forum"])
        self.stdout.write(f"Attached publication {publication.pk} → {forum} ({reason})")
