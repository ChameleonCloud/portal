import logging
from projects.user_publication import scopus, semantic_scholar, gscholar
from projects.user_publication.utils import export_publications, report_publications

logger = logging.getLogger(__name__)


def import_pubs(dry_run=True, file_name=""):
    pubs = []
    pubs.extend(scopus.pub_import(dry_run))
    pubs.extend(semantic_scholar.pub_import(dry_run))
    pubs.extend(gscholar.pub_import(dry_run))
    # displays them on console
    report_publications(pubs)
    if file_name:
        export_publications(pubs, file_name)
    return pubs
