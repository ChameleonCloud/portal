import logging
from projects.user_publication import scopus, semantic_scholar, gscholar
from projects.user_publication.utils import export_publications, report_publications

logger = logging.getLogger(__name__)


def _is_same_publication(o_pub, d_pub):
    # check if original publication is same as duplicate
    if o_pub.title == d_pub.title and o_pub.year == d_pub.year:
        return True
    return False


def _get_unique_pubs(pubs):
    pub_titles = {}
    for p in pubs:
        o_pub = pub_titles.get(p.title, None)
        if not o_pub:
            # first seen - update the dict with publication
            pub_titles[p.title] = p
            continue
        if _is_same_publication(o_pub, p):
            logger.info(
                f"removing duplicate publication {p} - original publication - {o_pub}"
            )
            pubs.remove(p)
    return pubs


def import_pubs(dry_run=True, file_name=""):
    pubs = []
    pubs.extend(gscholar.pub_import(dry_run))
    pubs.extend(scopus.pub_import(dry_run))
    pubs.extend(semantic_scholar.pub_import(dry_run))
    pubs = _get_unique_pubs(pubs)
    # displays them on console
    report_publications(pubs)
    if file_name:
        export_publications(pubs, file_name)
    if not dry_run:
        for pub in pubs:
            pub.save()
    return pubs
