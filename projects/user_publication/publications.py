# Contains functions to import publications for various sources
# Also contains functions to review imported publications

import logging

from celery.decorators import task

from projects.models import Publication
from projects.user_publication import openalex, science_direct, scopus, semantic_scholar
from projects.user_publication.utils import (
    add_source_to_pub,
    data_to_publication,
    get_publications_with_same_attributes,
    update_progress,
)

LOG = logging.getLogger(__name__)


@task(bind=True)
def import_pubs_scopus_task(self):
    return import_pubs_task(self, "scopus")


@task(bind=True)
def import_pubs_semantic_scholar_task(self):
    return import_pubs_task(self, "semantic_scholar")


@task(bind=True)
def import_pubs_science_direct_task(self):
    return import_pubs_task(self, "science_direct")


@task(bind=True)
def import_pubs_openalex_task(self):
    return import_pubs_task(self, "openalex")


@task(bind=True)
def update_citations_task(self):
    for pub in Publication.objects.filter(status=Publication.STATUS_APPROVED):
        LOG.info("Updating citations for %s", pub.id)
        scopus.update_citation(pub)
        semantic_scholar.update_citation(pub)


def import_pubs_task(self, source):
    LOG.info("Importing %s publications", source)
    try:
        import_pubs(self, source=source)
    except Exception as e:
        self.update_state(state="ERROR")
        LOG.error("Error importing %s publications: %s %s", source, type(e), e)
        raise
    return "Completed"


def import_pubs(task, source="all"):
    """Import publications from external sources and persist them via Django ORM.

    Args:
        task: Celery task instance.
        source: One of ``scopus``, ``semantic_scholar``, ``science_direct``,
            ``openalex``, or ``all``.
    """
    pubs = []

    if source in ("scopus", "all"):
        pubs.extend(scopus.pub_import(task))
    if source in ("semantic_scholar", "all"):
        pubs.extend(semantic_scholar.pub_import(task))
    if source in ("science_direct", "all"):
        pubs.extend(science_direct.pub_import(task))
    if source in ("openalex", "all"):
        pubs.extend(openalex.pub_import(task))

    # Process each found publication
    for i, pub_data in enumerate(pubs):
        try:
            update_progress(stage=1, current=i, total=len(pubs), task=task)

            # Convert PublicationData to an unsaved Publication model for comparison
            pub_comparison = data_to_publication(pub_data)

            # get matching pubs in DB, add this as a source, continue to next new pub.
            same_pubs = get_publications_with_same_attributes(
                pub_comparison, Publication
            )
            if len(same_pubs) > 0:
                for same_pub in same_pubs:
                    add_source_to_pub(same_pub, pub_data)
                continue

            # If all conditions are met, import the publication
            LOG.info("Import %s", pub_data)
            pub_comparison.added_by_username = "admin"
            pub_comparison.save()
            add_source_to_pub(pub_comparison, pub_data)

        except Exception as e:
            LOG.error(
                "Error processing publication %s from %s",
                getattr(pub_data, "title", "?"),
                source,
            )
            LOG.exception(e)
            continue
