import logging

from django.conf import settings

from projects.models import ChameleonPublication
from projects.user_publication.utils import update_progress
from magpub.sources.openalex import OpenAlexClient

logger = logging.getLogger("projects")


def pub_import(task, dry_run=True):
    """Import publications from OpenAlex.

    Returns a list of PublicationData objects.
    """
    client = OpenAlexClient(mailto=settings.OPENALEX_MAILTO)
    publications = []

    chameleon_pubs = ChameleonPublication.objects.exclude(openalex_ref__isnull=True)
    total = len(chameleon_pubs)

    for i, chameleon_pub in enumerate(chameleon_pubs):
        update_progress(stage=0, current=i, total=total, task=task)
        for pub_data in client.get_citations(chameleon_pub.openalex_ref):
            publications.append(pub_data)

    return publications
