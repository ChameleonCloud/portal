"""
Django-specific helpers for the publication import pipeline.

This module sits between the Django ORM / Celery and the Django-agnostic
``util.publications`` library. It handles:
  - Mapping between ``Publication`` / ``RawPublication`` models and
    ``PublicationData``.
  - Progress reporting for Celery tasks.
  - Chameleon-specific lookups (Keycloak, project allocation dates).

For pure publication logic (BibTeX parsing, similarity, deduplication,
external API clients) see ``util.publications``.
"""

import datetime
import logging

import pytz
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from projects.models import RawPublication
from util.keycloak_client import KeycloakClient
from magpub.deduplicate import find_matches
from magpub.models import PublicationData
from magpub import utils as pub_utils

LOG = logging.getLogger(__name__)

# Re-export the pure utilities so legacy call sites keep working.
PublicationUtils = pub_utils


def update_progress(task, stage=None, current=None, total=None, message=None):
    """Update Celery task progress.

    This is essentially 2 different progress bars depending on stage.
    Stage: 0 - import, 1 - processing.
    """
    if message:
        task.update_state(state="PROGRESS", meta={"message": message})
    else:
        stage_multiplier = 50 / total
        stage_offset = stage * 50
        calculated_current = int(current * stage_multiplier + stage_offset)
        LOG.info(
            "Updating task progress: %s/%s -> %s/100",
            current,
            total,
            calculated_current,
        )
        task.update_state(
            state="PROGRESS",
            meta={"current": calculated_current, "total": 100},
        )


# ---------------------------------------------------------------------------
# Model <-> PublicationData bidirectional mapping
# ---------------------------------------------------------------------------

def publication_to_data(pub) -> PublicationData:
    """Convert a ``projects.models.Publication`` instance to ``PublicationData``."""
    return PublicationData(
        title=pub.title,
        author=pub.author,
        year=pub.year,
        month=pub.month,
        forum=pub.forum,
        publication_type=pub.publication_type,
        doi=pub.doi,
        link=pub.link,
        bibtex_source=pub.bibtex_source,
        source_name=getattr(pub.raw_sources.first(), "name", None) if hasattr(pub, "raw_sources") else None,
    )


def data_to_publication(data: PublicationData):
    """Build an **unsaved** ``Publication`` model from ``PublicationData``.

    The returned instance has not been persisted to the database.
    """
    from projects.models import Publication

    pub = Publication()
    pub.title = data.title
    pub.author = data.author
    pub.year = data.year
    pub.month = data.month
    pub.forum = data.forum
    pub.publication_type = data.publication_type
    pub.doi = data.doi
    pub.link = data.link
    pub.bibtex_source = data.bibtex_source or "{}"
    pub.status = Publication.STATUS_SUBMITTED
    return pub


def raw_publication_to_data(raw: RawPublication) -> PublicationData:
    """Convert a ``RawPublication`` instance to ``PublicationData``."""
    return PublicationData(
        title=raw.title,
        author=raw.author,
        year=raw.year,
        month=raw.month,
        forum=raw.forum,
        publication_type=raw.publication_type,
        doi=raw.doi,
        link=raw.link,
        bibtex_source=raw.bibtex_source,
        source_name=raw.name,
        source_id=raw.source_id,
        citation_count=raw.citation_count,
    )


# ---------------------------------------------------------------------------
# Chameleon-specific helpers
# ---------------------------------------------------------------------------

def is_project_prior_to_publication(project, pub_year):
    """Return True if *project* has an allocation starting on or before *pub_year*."""
    fake_start = datetime.datetime(year=9999, month=1, day=1, tzinfo=pytz.UTC)
    try:
        start = min(
            alloc.start_date or fake_start for alloc in project.allocations.all()
        )
    except ValueError:
        start = fake_start
    return start.year <= pub_year


def get_users_for_author(author):
    """Return Django ``User``s whose name matches *author* or a PI alias."""
    from projects.models import ProjectPIAlias

    author = pub_utils.decode_unicode_text(author)
    try:
        first_name, *_, last_name = author.rsplit(" ", 1)
    except ValueError:
        name_filter = Q(last_name=author)
    else:
        name_filter = Q(first_name__iexact=first_name, last_name__iexact=last_name)

    aliases = ProjectPIAlias.objects.filter(alias__iexact=author)
    for alias in aliases.all():
        name_filter |= Q(
            first_name__iexact=alias.pi.first_name,
            last_name__iexact=alias.pi.last_name,
        )

    return list(User.objects.filter(name_filter))


def get_projects_for_author_names(author_names, year):
    """Return Chameleon charge codes for projects associated with *author_names*."""
    users = []
    for author in author_names:
        users.extend(get_users_for_author(author))
    kcc = KeycloakClient()
    return [
        proj for u in users for proj in kcc.get_user_projects_by_user(u)
    ]


# ---------------------------------------------------------------------------
# Import-pipeline helpers (operate on Django models)
# ---------------------------------------------------------------------------

def get_publications_with_same_attributes(pub, publication_model_class):
    """Return publications that are likely duplicates of *pub*.

    Results are ordered: approved first, then everything else.
    """
    # Exact-field query matches (fast path via ORM)
    similar_pub = publication_model_class.objects.filter(
        Q(
            title__iexact=pub.title,
            forum__iexact=pub.forum,
            author__iexact=pub.author,
            year=pub.year,
        )
    ).exclude(id=getattr(pub, "id", None))

    if pub.doi and not similar_pub.exists():
        similar_pub = publication_model_class.objects.filter(doi__iexact=pub.doi)

    if hasattr(pub, "raw_publications"):
        similar_pub = (
            similar_pub
            | publication_model_class.objects.filter(
                raw_publications__source_id__in=pub.raw_publications.values_list(
                    "source_id", flat=True
                )
            )
            .exclude(id=getattr(pub, "id", None))
            .distinct()
        )

    approved = similar_pub.filter(status=publication_model_class.STATUS_APPROVED)
    others = similar_pub.exclude(
        status=publication_model_class.STATUS_APPROVED
    ).exclude(status="DUPLICATE")
    return list(approved) + list(others)


def add_source_to_pub(pub, raw_pub):
    """Attach (or update) the raw source described by *raw_pub* on *pub*.

    *raw_pub* may be either a ``RawPublication`` model or a
    ``PublicationData`` instance.
    """
    if isinstance(raw_pub, PublicationData):
        source_name = raw_pub.source_name
        source_id = raw_pub.source_id
    else:
        source_name = raw_pub.source_name
        source_id = raw_pub.source_id

    LOG.info(
        "Publication already exists - %s - %s - adding other source - %s",
        getattr(pub, "id", "?"),
        getattr(pub, "title", "?"),
        source_name,
    )

    with transaction.atomic():
        source = RawPublication.objects.filter(source_id=source_id).first()
        if not source:
            source = RawPublication.objects.filter(
                name=source_name, publication=pub
            ).first()
        if not source:
            source = RawPublication.from_publication(pub, source_name)
            source.name = source_name

        source.publication = pub
        source.source_id = source_id
        source.is_found_by_algorithm = True
        source.cites_chameleon = True

        if pub.status == pub.STATUS_APPROVED:
            source.approved_with = source.APPROVED_WITH_PUBLICATION
        else:
            source.approved_with = None
        source.save()

        if isinstance(raw_pub, PublicationData):
            cites_id = raw_pub.extra.get("cites_chameleon_pub_id")
            query = raw_pub.extra.get("found_with_query")
        else:
            # Legacy RawPublicationSource-like object
            cites_id = getattr(raw_pub, "cites_chameleon_pub", None)
            query = getattr(raw_pub, "found_with_query", None)

        # Resolve IDs to model instances if needed
        from projects.models import ChameleonPublication, PublicationQuery
        if cites_id and not isinstance(cites_id, ChameleonPublication):
            try:
                cites_id = ChameleonPublication.objects.get(pk=cites_id)
            except ChameleonPublication.DoesNotExist:
                cites_id = None
        if query and not isinstance(query, PublicationQuery):
            try:
                query = PublicationQuery.objects.get(pk=query)
            except PublicationQuery.DoesNotExist:
                query = None

        update_cites_and_query(source, cites_id, query)


def update_cites_and_query(source, cites_chameleon_pub_obj, found_with_query_obj):
    """Update M2M relationships on a ``RawPublication``."""
    if cites_chameleon_pub_obj and not source.chameleon_publications.filter(
        pk=cites_chameleon_pub_obj.pk
    ).exists():
        source.chameleon_publications.add(cites_chameleon_pub_obj)
        source.save()

    if found_with_query_obj and not source.publication_queries.filter(
        pk=found_with_query_obj.pk
    ).exists():
        source.publication_queries.add(found_with_query_obj)
        source.save()
