import logging

from django.conf import settings

from projects.models import PublicationQuery, RawPublication
from magpub.sources.science_direct import ScienceDirectClient

logger = logging.getLogger("projects")


def pub_import(task, dry_run=True):
    """Import publications from ScienceDirect.

    Returns a list of PublicationData objects.
    """
    client = ScienceDirectClient(
        api_key=settings.SCOPUS_API_KEY,
        institution_token=settings.SCOPUS_INSTITUTION_KEY,
    )
    publications = []

    for query in PublicationQuery.objects.filter(
        source_type=RawPublication.SCIENCE_DIRECT
    ):
        for pub_data in client.search(query.query):
            pub_data.extra["found_with_query"] = str(query.query)
            publications.append(pub_data)

    return publications
