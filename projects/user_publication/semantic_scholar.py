import logging

from django.conf import settings

from projects.models import ChameleonPublication, PublicationCitation, RawPublication
from projects.user_publication.utils import (
    update_progress,
)
from magpub.sources.semantic_scholar import SemanticScholarClient

logger = logging.getLogger("projects")


def pub_import(task, dry_run=True):
    """Import publications from Semantic Scholar.

    Returns a list of PublicationData objects.
    """
    client = SemanticScholarClient(api_key=settings.SEMANTIC_SCHOLAR_API_KEY)
    publications = []

    chameleon_pubs = ChameleonPublication.objects.exclude(
        semantic_scholar_ref__isnull=True
    )
    total = len(chameleon_pubs)
    for i, chameleon_pub in enumerate(chameleon_pubs):
        update_progress(stage=0, current=i, total=total, task=task)
        for pub_data in client.search_citations(chameleon_pub.semantic_scholar_ref):
            publications.append(pub_data)

    from projects.models import PublicationQuery
    for query in PublicationQuery.objects.filter(source_type=RawPublication.SEMANTIC_SCHOLAR):
        for pub_data in client.bulk_search(query.query):
            publications.append(pub_data)

    return publications


def update_citation(pub):
    """Update Semantic Scholar citation count for *pub*."""
    client = SemanticScholarClient(api_key=settings.SEMANTIC_SCHOLAR_API_KEY)

    try:
        raw_pub = pub.raw_sources.filter(name=RawPublication.SEMANTIC_SCHOLAR).first()
        source_id = None
        if raw_pub:
            source_id = raw_pub.source_id

        if not source_id:
            try:
                if pub.citation.semantic_scholar_source_id:
                    source_id = pub.citation.semantic_scholar_source_id
            except PublicationCitation.DoesNotExist:
                pass

        if not source_id:
            results = client.search_paper(pub.title, fields=["paperId", "citationCount", "title"])
            if results:
                for result in results:
                    if getattr(result, "title", "").lower() == pub.title.lower():
                        source_id = getattr(result, "source_id", None)
                        break

        if source_id:
            count = client.get_citation_count(source_id)
            if raw_pub:
                raw_pub.citation_count = count
                raw_pub.save()

            pub_citation, _ = PublicationCitation.objects.get_or_create(publication=pub)
            pub_citation.semantic_scholar_source_id = source_id
            pub_citation.semantic_scholar_citation_count = count
            pub_citation.save()

    except Exception as e:
        logger.error("Error updating semantic scholar citations for %s: %s", pub.id, e)
        logger.exception(e)
