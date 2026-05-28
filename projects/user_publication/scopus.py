import logging

from django.conf import settings

from projects.models import PublicationCitation, RawPublication
from projects.user_publication.utils import (
    update_progress,
)
from magpub.sources.scopus import ScopusClient

logger = logging.getLogger("projects")


def pub_import(task, dry_run=True):
    """Import publications from Scopus via configured queries.

    Args:
        task: Celery task instance (for progress reporting).
        dry_run: If True, yield results without persisting.

    Returns:
        List of PublicationData objects (legacy callers expect a list).
    """
    from projects.models import PublicationQuery

    client = ScopusClient(
        api_key=settings.SCOPUS_API_KEY,
        institution_token=settings.SCOPUS_INSTITUTION_KEY,
    )
    publications = []
    for query in PublicationQuery.objects.filter(source_type=RawPublication.SCOPUS):
        search = None
        try:
            import pybliometrics
            from pybliometrics.scopus import ScopusSearch
            search = ScopusSearch(query.query)
        except Exception as e:
            logger.error("ScopusSearch failed for query %s: %s", query.query, e)
            continue

        results = getattr(search, "results", []) or []
        for i, raw_pub in enumerate(results):
            try:
                update_progress(stage=0, current=i, total=len(results), task=task)
                pub_data = client._raw_to_data(raw_pub)
                pub_data.source_name = RawPublication.SCOPUS
                pub_data.source_id = raw_pub.eid
                pub_data.extra["found_with_query"] = query
                publications.append(pub_data)
            except Exception as e:
                logger.error("Error processing publication %s: %s", getattr(raw_pub, "eid", "?"), e)
                logger.exception(e)
                continue

    return publications


def update_citation(pub):
    """Update Scopus citation count for *pub* (a Django Publication)."""
    client = ScopusClient(
        api_key=settings.SCOPUS_API_KEY,
        institution_token=settings.SCOPUS_INSTITUTION_KEY,
    )

    try:
        raw_pub = pub.raw_sources.filter(name=RawPublication.SCOPUS).first()
        source_id = None
        if raw_pub:
            source_id = raw_pub.source_id

        if not source_id:
            try:
                if pub.citation.scopus_source_id:
                    source_id = pub.citation.scopus_source_id
            except PublicationCitation.DoesNotExist:
                pass

        if not source_id:
            query = f"TITLE({pub.title})"
            search = None
            try:
                from pybliometrics.scopus import ScopusSearch
                search = ScopusSearch(query)
            except Exception:
                pass
            if search and search.results:
                for result in search.results:
                    result_title = result.title or ""
                    if result_title.lower() == pub.title.lower():
                        source_id = result.eid
                        break

        if source_id:
            citation = client.get_citations(source_id)

            if raw_pub:
                raw_pub.citation_count = citation.citation_count
                raw_pub.save()

            pub_citation, _ = PublicationCitation.objects.get_or_create(publication=pub)
            pub_citation.scopus_source_id = source_id
            pub_citation.scopus_citation_count = citation.citation_count
            pub_citation.save()

    except Exception as e:
        logger.error("Error updating scopus citations for %s: %s", pub.id, e)
        logger.exception(e)
