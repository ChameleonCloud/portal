import datetime
import logging

from django.conf import settings
import pybliometrics
from pybliometrics.scopus import AbstractRetrieval, ScopusSearch, CitationOverview

from projects.models import (
    ChameleonPublication,
    Publication,
    PublicationQuery,
    RawPublication,
)
from projects.user_publication import utils
from projects.user_publication.utils import (
    PublicationUtils,
    RawPublicationSource,
    update_progress,
)

logger = logging.getLogger("projects")


def _get_references(a):
    return a.references if a.references else []


def _scopus_pub_to_model(raw_pub):
    title = utils.decode_unicode_text(raw_pub.title)
    published_on = datetime.datetime.strptime(raw_pub.coverDate, "%Y-%m-%d")
    year = published_on.year
    # get the author names with decoded unicode characters
    author_names = utils.decode_unicode_text(raw_pub.author_names)
    # authors as a list of strings "firstname lastname" format
    authors = [utils.format_author_name(author) for author in author_names.split(";")]
    doi = raw_pub.doi if raw_pub.doi else ""
    link = ""
    if doi:
        link = f"https://www.doi.org/{doi}"
    pub_model = Publication(
        title=title,
        year=year,
        month=published_on.month,
        author=" and ".join(authors),
        publication_type=PublicationUtils.get_pub_type(
            {"ENTRYTYPE": raw_pub.subtypeDescription}
        ),
        bibtex_source="{}",
        added_by_username="admin",
        forum=raw_pub.publicationName,
        doi=doi,
        link=link,
        status=Publication.STATUS_SUBMITTED,
    )
    return pub_model


def pub_import(task, dry_run=True):
    pybliometrics.scopus.init(
        config_path="/project/pybliometrics.cfg",
        keys=[settings.SCOPUS_API_KEY],
        inst_tokens=[settings.SCOPUS_INSTITUTION_KEY],
    )
    publications = []
    for query in PublicationQuery.objects.filter(source_type=RawPublication.SCOPUS):
        search = ScopusSearch(query.query)
        logger.debug("Performed search")
        for i, raw_pub in enumerate(search.results):
            try:
                update_progress(
                    stage=0, current=i, total=len(search.results), task=task
                )
                pub_model = _scopus_pub_to_model(raw_pub)
                logger.info(
                    f"Processing publication {raw_pub.eid} - {pub_model.title} - {query.query}"
                )
                publications.append(
                    RawPublicationSource(
                        pub_model=pub_model,
                        source_id=raw_pub.eid,
                        source_name=RawPublication.SCOPUS,
                        cites_chameleon_pub=None,
                        found_with_query=query,
                    )
                )
            except Exception as e:
                # TODO  we keep hitting this
                logger.error(f"Error processing publication {raw_pub.eid}: {e}")
                logger.exception(e)
                continue
    return publications


def update_citations():
    # for each rawpublication that is scopus, from an approved publication
    pybliometrics.scopus.init(
        config_path="/project/pybliometrics.cfg",
        keys=[settings.SCOPUS_API_KEY],
        inst_tokens=[settings.SCOPUS_INSTITUTION_KEY],
    )

    for pub in RawPublication.objects.filter(
        name=RawPublication.SCOPUS,
        publication__status=Publication.STATUS_APPROVED,
        source_id__isnull=False,
    ).select_related("publication"):
        ab = AbstractRetrieval(pub.source_id, view="REF")
        c = 0
        if ab.citedby_count:
            c = ab.citedby_count
        pub.citation_count = c
        pub.save()
