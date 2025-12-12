# Contains functions to import publications for various sources
# Also contains functions to review imported publications

import logging

from projects.models import (
    Publication,
    RawPublication,
)
from projects.user_publication import scopus, semantic_scholar, utils
from projects.user_publication.utils import update_progress
from celery.decorators import task

LOG = logging.getLogger(__name__)


@task(bind=True)
def import_pubs_scopus_task(self):
    return import_pubs_task(self, "scopus")


@task(bind=True)
def import_pubs_semantic_scholar_task(self):
    return import_pubs_task(self, "semantic_scholar")


@task(bind=True)
def update_scopus_citations_task(self):
    scopus.update_citations()


@task(bind=True)
def update_semantic_scholar_citations_task(self):
    semantic_scholar.update_citations()


def import_pubs_task(self, source):
    LOG.info("Importing publications")
    try:
        import_pubs(self, source=source)
    except Exception as e:
        self.update_state(state="ERROR")
        LOG.error(f"Error importing {source} publications: {type(e)} {e}")
        raise
    return "Completed"


def import_pubs(task, source="all"):
    """Invoke import_pubs() interactively in django manage.py shell

    Args:
        dry_run (bool, optional): False means stores the publications in DB. Defaults to True.
        source (str, optional): scopus, semantic_scholar as options. Defaults to "all".
    """
    pubs = []

    # Import publications from different sources based on the input argument
    if source in ["scopus", "all"]:
        pubs.extend(scopus.pub_import(task))
    if source in ["semantic_scholar", "all"]:
        pubs.extend(semantic_scholar.pub_import(task))

    # Process each found publication
    for i, raw_pub in enumerate(pubs):
        try:
            update_progress(stage=1, current=i, total=len(pubs), task=task)
            # get matching pubs in DB, add this as a source, continue to next new pub.
            same_pubs = utils.get_publications_with_same_attributes(
                raw_pub.pub_model, Publication
            )
            if same_pubs.exists():
                for same_pub in same_pubs:
                    utils.add_source_to_pub(same_pub, raw_pub)
                continue

            # If all conditions are met, import the publication
            else:
                LOG.info(f"import {raw_pub.pub_model.__repr__()}")
                # Save the publication if it is not a dry run
                utils.add_source_to_pub(raw_pub.pub_model, raw_pub)
                source.approved_with = None
                source.save()

        except Exception as e:
            LOG.error(
                f"Error processing publication {raw_pub.pub_model.title} from {source}"
            )
            LOG.exception(e)
            continue
