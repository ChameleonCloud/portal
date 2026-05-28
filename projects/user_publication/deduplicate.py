"""
Django adapter for publication deduplication.

The heavy lifting lives in ``util.publications.deduplicate``. This module
provides ORM wrappers so existing callers (admin, views, migrations) keep
working with Django model objects.
"""

import logging

from projects.models import Publication
from magpub.deduplicate import find_matches
from magpub.utils import is_pub_similar
from projects.user_publication.utils import publication_to_data

logger = logging.getLogger(__name__)


def get_originals_for_duplicate_pub(dpub):
    """Return original pubs that are almost the same as *dpub*.

    Backwards-compatible wrapper used by the admin duplicate filter
    and ``PublicationAdmin.potential_duplicate_of``.
    """
    pubs_to_check_against = (
        Publication.objects.filter(checked_for_duplicates=True)
        .exclude(id=dpub.id)
        .exclude(status="DUPLICATE")
        .order_by("id")
    )

    dpub_data = publication_to_data(dpub)
    existing_data = [publication_to_data(p) for p in pubs_to_check_against]
    matched_data = find_matches(dpub_data, existing_data)

    # Map matched PublicationData back to Django models
    matched_titles = {m.title for m in matched_data}
    return [p for p in pubs_to_check_against if p.title in matched_titles]


def get_duplicate_pubs(pubs=None):
    """Return a dict mapping potential duplicates → list of originals.

    If *pubs* are not saved in the database the function may fail because
    it needs the publication ID. Consider using
    ``util.publications.deduplicate.group_duplicates`` directly for unsaved
    ``PublicationData`` objects.
    """
    duplicate_map = {}

    if pubs:
        pubs_to_check = pubs
    else:
        pubs_to_check = Publication.objects.filter(
            checked_for_duplicates=False
        ).order_by("-id")

    for pub1 in pubs_to_check:
        if not pub1.year:
            logger.info("%s does not have year - ignoring", pub1.title)
            continue
        originals = get_originals_for_duplicate_pub(pub1)
        if originals:
            duplicate_map[pub1] = originals

    return duplicate_map
