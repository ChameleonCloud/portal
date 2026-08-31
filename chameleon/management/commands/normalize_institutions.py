from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction
import json
import logging
import re
import requests as http_requests
from util.keycloak_client import KeycloakClient


from chameleon.models import Institution, InstitutionAlias, UserInstitution

from openai import OpenAI

LOG = logging.getLogger(__name__)

# Used for the `has_signal` check in phrase shortening: stops shortening when only
# these words remain (no useful content left to search on).
INSTITUTION_STOPWORDS = frozenset([
    "the", "a", "an", "of", "at", "in", "for", "and", "or", "by", "on",
    "university", "universities", "college", "colleges", "institute",
    "institutes", "institution", "school", "academy", "center", "centre",
    "national", "international", "state", "community", "technical",
    "polytechnic", "foundation", "research",
    "new", "san", "los", "las", "el", "la", "de", "del",
    "city", "bay", "fort", "port", "mount", "lake", "valley", "hill", "hills",
])

# Narrower set used when selecting OR-query words in Strategy 2.  Directional
# words ("western", "eastern", …) are intentionally excluded here so that
# "Western Michigan" and "Eastern Michigan" produce different candidate sets.
OR_STOPWORDS = frozenset([
    "the", "a", "an", "of", "at", "in", "for", "and", "or", "by", "on",
    "university", "universities", "college", "colleges", "institute",
    "institutes", "institution", "school", "academy", "center", "centre",
    "community", "technical", "polytechnic", "foundation", "research",
    "new", "san", "los", "las", "el", "la", "de", "del",
    "city", "bay", "fort", "port", "mount", "lake", "valley", "hill", "hills",
])


# Common non-English city names users type for major research university cities
CITY_TRANSLATIONS = {
    "torino": "Turin", "milano": "Milan", "roma": "Rome",
    "napoli": "Naples", "venezia": "Venice", "firenze": "Florence",
    "genova": "Genoa", "köln": "Cologne", "münchen": "Munich",
    "wien": "Vienna", "zürich": "Zurich", "bruxelles": "Brussels",
}


def _translate_cities(name):
    """Replace known non-English city names with English equivalents."""
    words = name.split()
    translated = [CITY_TRANSLATIONS.get(w.lower(), w) for w in words]
    return " ".join(translated)


def _normalize_name(name):
    """Replace comma/dash separators with spaces and collapse whitespace."""
    name = re.sub(r"\s*[,\-]\s*", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _name_variants(raw_value):
    """
    Return deduped name variants to try for exact matching:
    original, with/without 'The ', separator-normalized, and city-translated forms.
    """
    def with_the_variants(s):
        if s.lower().startswith("the "):
            return [s, s[4:]]
        return [s, "The " + s]

    variants = with_the_variants(raw_value)
    norm = _normalize_name(raw_value)
    if norm != raw_value:
        variants += with_the_variants(norm)
    translated = _translate_cities(norm)
    if translated != norm:
        variants += with_the_variants(translated)
    return list(dict.fromkeys(variants))  # deduplicate, preserve order


def _distinctive_word(query):
    """Return the first word that is long enough and not a generic stopword."""
    for word in query.split():
        w = word.lower().rstrip(".,;:")
        if len(w) >= 3 and w not in INSTITUTION_STOPWORDS:
            return word
    return query.split()[0] if query.split() else ""


def _llm_candidates(query):
    """
    Return up to 25 candidate institutions for the LLM to choose from.

    Strategy (tries in order, returns first batch with >= 3 hits):
    1. Progressive phrase shortening on the normalized query — catches "University of
       Wisconsin" → all UW campuses, and "Texas State University San Marcos" → drops
       last word until "Texas State University" matches.
    2. OR across all distinctive words with relevance scoring — catches foreign/translated
       names and cases where distinctive words are spread across the name.
    """
    from django.db.models import Case, When, IntegerField, Value
    from django.db.models.functions import Length

    normalized = _normalize_name(query)
    words = normalized.split()
    phrase_hits = []

    # Strategy 1: progressive phrase shortening
    while words:
        # Only search if the phrase still contains at least one non-stopword of length >= 3
        has_signal = any(
            w.lower() not in INSTITUTION_STOPWORDS and len(w) >= 3 for w in words
        )
        if not has_signal:
            break
        phrase = " ".join(words)
        results = list(
            Institution.objects.filter(
                Q(name__icontains=phrase) | Q(aliases__alias__icontains=phrase)
            )
            .distinct()
            .annotate(name_len=Length("name"))
            .order_by("name_len")
            .values("id", "name", "state", "country")[:25]
        )
        if len(results) >= 3:
            return results
        if results:  # 1-2 hits — keep them, add OR results below
            phrase_hits = results
            break
        words.pop()  # drop rightmost word and retry

    # Strategy 2: OR across all distinctive words, scored by match count.
    # Uses OR_STOPWORDS (not INSTITUTION_STOPWORDS) so directional words like
    # "western"/"eastern" are included — they're the only difference between
    # schools like Western Michigan and Eastern Michigan.
    distinctive = [
        w for w in re.split(r"\s+", normalized)
        if len(w) >= 3 and w.lower() not in OR_STOPWORDS
    ][:4]
    if not distinctive:
        return phrase_hits

    q = Q()
    for w in distinctive:
        q |= Q(name__icontains=w)

    score = Case(
        When(Q(name__icontains=distinctive[0]), then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )
    for w in distinctive[1:]:
        score = score + Case(
            When(Q(name__icontains=w), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )

    or_results = list(
        Institution.objects.filter(q)
        .annotate(score=score, name_len=Length("name"))
        .order_by("-score", "name_len")
        .distinct()
        .values("id", "name", "state", "country")[:25]
    )

    # Merge: phrase hits first (exact phrase is best signal), then OR hits
    seen = {r["id"] for r in phrase_hits}
    combined = phrase_hits + [r for r in or_results if r["id"] not in seen]
    return combined[:25]


FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "msn.com", "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com", "mac.com",
    "aol.com", "protonmail.com", "proton.me", "fastmail.com", "zoho.com",
})


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

        import threading
        _thread_local = threading.local()

        def _init_thread():
            _thread_local.kc = KeycloakClient()

        def fetch_and_process(user):
            try:
                kc_user = _thread_local.kc.get_user_from_portal_user(user)
                if kc_user:
                    self.stdout.write(f"Processing user {user.pk} ({user.username})")
                    self.process_user(user, kc_user)
            except Exception as e:
                LOG.warning(f"Failed to process user {user.pk} ({user.username}): {e}")

        with ThreadPoolExecutor(max_workers=50, initializer=_init_thread) as executor:
            futures = [executor.submit(fetch_and_process, u) for u in users.iterator()]
            for future in as_completed(futures):
                future.result()

    def process_user(self, user, kc_user):
        domain = self.extract_domain(user)

        # Don't use a free-email domain as an institution signal, but still
        # process affiliationInstitution if the user supplied one.
        if domain and domain in FREE_EMAIL_DOMAINS:
            domain = None

        # kc_user is already the attributes dict (from get_all_users_attributes)
        raw_value = kc_user.get("affiliationInstitution") if kc_user else None
        if isinstance(raw_value, list):
            raw_value = raw_value[0] if raw_value else None
        if raw_value:
            raw_value = raw_value.strip()

        # 1. Exact alias match — try original + "The " variants + separator-normalized forms
        if raw_value:
            for v in _name_variants(raw_value):
                alias = (
                    InstitutionAlias.objects.filter(alias__iexact=v)
                    .select_related("institution")
                    .first()
                )
                if alias:
                    self.attach_user(user, alias.institution, reason="exact alias")
                    return

        # 2. Exact institution name match — same variants
        if raw_value:
            for v in _name_variants(raw_value):
                inst = Institution.objects.filter(name__iexact=v).first()
                if inst:
                    self.attach_user(user, inst, reason="institution name")
                    return

        # 3. Email domain match — try exact domain then progressively strip subdomains
        if domain:
            inst = self._match_by_domain(domain)
            if inst:
                self.attach_user(user, inst, reason="website domain")
                return

        # 4. ROR API lookup
        query = raw_value or domain or ""
        if query:
            inst = self.lookup_ror(query, raw_value)
            if inst:
                self.attach_user(user, inst, reason="ROR API")
                return

        # 5. OpenAI fallback — match against fuzzy candidates only, never create new records
        if query:
            inst = self.match_via_llm(query, raw_value)
            if inst:
                self.attach_user(user, inst, reason="LLM match")
                return

        self.stdout.write(
            self.style.WARNING(
                f"  Could not normalize institution for user {user.pk}: '{query}'"
            )
        )

    def extract_domain(self, user):
        email = getattr(user, "email", "") or ""
        if "@" in email:
            return email.split("@", 1)[1].lower()
        return None

    def _match_by_domain(self, domain):
        """
        Try exact domain match, then progressively strip subdomains.
        e.g. "cs.uchicago.edu" → try "cs.uchicago.edu", then "uchicago.edu".
        Stops before single-part TLDs like "edu" or "com".
        """
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            candidate = ".".join(parts[i:])
            if candidate.count(".") == 0:
                break  # skip bare TLDs
            inst = Institution.objects.filter(website_domain__iexact=candidate).first()
            if inst:
                return inst
        return None

    def lookup_ror(self, query, raw_value):
        """Query the ROR public API and return a matched/created Institution, or None."""
        ROR_TYPE_MAP = {
            "Education": Institution.InstitutionType.OTHER,
            "Company": Institution.InstitutionType.INDUSTRY,
            "Government": Institution.InstitutionType.GOVERNMENT,
            "Nonprofit": Institution.InstitutionType.NONPROFIT,
            "Healthcare": Institution.InstitutionType.NONPROFIT,
            "Facility": Institution.InstitutionType.OTHER,
            "Other": Institution.InstitutionType.OTHER,
            "Funder": Institution.InstitutionType.NONPROFIT,
        }
        try:
            resp = http_requests.get(
                "https://api.ror.org/organizations",
                params={"query": query},
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as exc:
            LOG.warning("ROR API error for %r: %s", query, exc)
            return None

        items = resp.json().get("items", [])
        if not items:
            return None

        top = items[0]
        if top.get("score", 0) < 0.85:
            return None

        ror_id = top.get("id", "").replace("https://ror.org/", "")
        name = top.get("name", "").strip()
        if not name:
            return None

        types = top.get("types", [])
        institution_type = Institution.InstitutionType.OTHER
        for t in types:
            if t in ROR_TYPE_MAP:
                institution_type = ROR_TYPE_MAP[t]
                break

        country_obj = top.get("country", {})
        country = country_obj.get("country_code", "")

        if self.dry_run:
            self.stdout.write(f"  [DRY-RUN] ROR match: {name} ({ror_id})")
            return None

        inst, _ = Institution.objects.get_or_create(
            ror_id=ror_id,
            defaults=dict(
                name=name,
                institution_type=institution_type,
                country=country,
                source=Institution.Source.CANONICAL,
            ),
        )
        if raw_value:
            InstitutionAlias.objects.get_or_create(institution=inst, alias=raw_value)
        return inst

    def match_via_llm(self, query, raw_value):
        """
        Use the LLM to pick the best match from fuzzy DB candidates.
        Never creates new Institution records — only picks from existing ones.
        Returns an Institution or None.
        """
        candidates = _llm_candidates(query)
        if not candidates:
            return None

        candidate_lines = "\n".join(
            f"{c['id']}: {c['name']}" + (f" ({c['state']})" if c['state'] else f" ({c['country']})")
            for c in candidates
        )
        prompt = (
            f"User-supplied institution: {query!r}\n\n"
            f"Candidates (id: name):\n{candidate_lines}\n\n"
            f'Return JSON: {{"id": <integer id of best match, or null if none match>}}'
        )
        system_prompt = (
            "You match a user-supplied institution string to a canonical institution list. "
            "Return the id of the best match, or null if no candidate is a clear match. "
            "Rules:\n"
            "- Ignore minor accent/diacritic differences (e.g. Mayaguez = Mayagüez).\n"
            "- Ignore punctuation differences (comma, dash, 'at' vs '-').\n"
            "- If the input is a university system name without a campus (e.g. 'University of "
            "Wisconsin', 'University of Colorado'), pick the flagship/main campus from the list.\n"
            "- Match translated names to their institution (e.g. 'University of Torino' = "
            "'Università degli Studi di Torino').\n"
            "Respond with ONLY valid JSON."
        )

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = "\n".join(content.split("\n")[1:-1])
            data = json.loads(content)
        except Exception as exc:
            LOG.warning("LLM match failed for %r: %s", query, exc)
            return None

        matched_id = data.get("id")
        if not matched_id:
            return None

        inst = Institution.objects.filter(pk=matched_id).first()
        if inst and raw_value:
            InstitutionAlias.objects.get_or_create(institution=inst, alias=raw_value[:500])
        return inst

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
