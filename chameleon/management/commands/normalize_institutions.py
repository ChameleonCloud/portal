from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
import json
from util.keycloak_client import KeycloakClient


from chameleon.models import Institution, InstitutionAlias, UserInstitution

from openai import OpenAI


class Command(BaseCommand):
    help = "Normalize user-supplied institution strings into Institution/UserInstitution models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without writing any changes to the database",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        if not self.dry_run and OpenAI is None:
            self.stdout.write(self.style.ERROR("openai package not installed"))
            return

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE_URL,
        )

        User = get_user_model()

        users = User.objects.filter(institutions__isnull=True)

        self.stdout.write(f"Processing {users.count()} users")

        keycloak_client = KeycloakClient()
        for user in users.iterator():
            kc_user = keycloak_client.get_user_by_username(user.username)
            if not kc_user:
                # Legacy user, no login since fed. identity
                continue
            self.process_user(user, kc_user)

    def process_user(self, user, kc_user):
        # Try to match user to a known institution or alias
        raw_value = kc_user.get("attributes", {}).get("affiliationInstitution")
        if raw_value:
            raw_value = raw_value.strip()

            alias = (
                InstitutionAlias.objects.filter(alias__iexact=raw_value)
                .select_related("institution")
                .first()
            )
            if alias:
                self.attach_user(user, alias.institution, reason="exact alias")
                return

            inst = Institution.objects.filter(name__iexact=raw_value).first()
            if inst:
                self.attach_user(user, inst, reason="institution name")
                return

        # Try to match by email domain
        domain = self.extract_domain(user)
        if domain and domain.endswith(".edu"):
            alias = (
                InstitutionAlias.objects.filter(alias__icontains=domain)
                .select_related("institution")
                .first()
            )
            if alias:
                self.attach_user(user, alias.institution, reason="edu domain")
                return

        # Use AI to generate an alias -> institution mapping
        if not raw_value:
            raw_value = domain or ""
        country = kc_user.get("attributes", {}).get("country")
        ai_data = self.generate_institution_metadata(raw_value, domain, country)
        if ai_data:
            inst, created = Institution.objects.get_or_create(
                name=ai_data["name"],
                defaults={
                    "state": ai_data["state"],
                    "institution_type": ai_data["institution_type"],
                    "source": Institution.Source.AI,
                    "source_comment": "Created via AI normalization",
                    "minority_serving_institution": False,
                    "epscor_state": False,
                },
            )
            InstitutionAlias.objects.get_or_create(institution=inst, alias=raw_value)
            self.attach_user(user, inst, reason="openai generated")

            # If it already existed from the canonical list, do NOT overwrite
            if not created:
                self.stdout.write(
                    f"Institution already exists: {inst.name} (source={inst.source})"
                )
        self.stdout.write(
            self.style.WARNING(
                f"Could not normalize institution for user {user.pk}: '{raw_value}'"
            )
        )

    def extract_domain(self, user):
        email = getattr(user, "email", "") or ""
        if "@" in email:
            return email.split("@", 1)[1].lower()
        return None

    def generate_institution_metadata(self, raw_value, domain, country):
        prompt = (
            f"Input: {raw_value}\n"
            f"Domain: {domain or 'unknown'}\n"
            f"Country: {country or 'unknown'}\n"
        )
        system_prompt = """
You normalize institutions.

Return JSON with the following keys:
- name: canonical institution name (string or empty)
- state: US state name or "n/a" if not US-based
- institution_type: one of [r1, r2, cc, government, nonprofit, industry, other, unknown]

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
            data = json.loads(content)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid AI JSON"))
            return None

        name = (data.get("name") or "").strip()
        if not name:
            return None

        return {
            "name": name[:500],
            "state": data.get("state", "n/a") or "n/a",
            "institution_type": data.get("institution_type", "unknown"),
        }

    @transaction.atomic
    def attach_user(self, user, institution, reason):
        if self.dry_run:
            self.stdout.write(
                f"[DRY-RUN] Would attach user {user.pk} to {institution.name} ({reason})"
            )
            return

        UserInstitution.objects.get_or_create(
            user=user,
            institution=institution,
        )
        self.stdout.write(f"Attached user {user.pk} to {institution.name} ({reason})")
