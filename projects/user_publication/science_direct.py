import datetime
import logging

from django.conf import settings
import pybliometrics
from pybliometrics.sciencedirect import ScienceDirectSearch

from projects.models import Publication, PublicationQuery, RawPublication
from projects.user_publication import utils
from projects.user_publication.utils import (
    RawPublicationSource,
    update_progress,
)

logger = logging.getLogger("projects")


def pub_import(task, dry_run=True):
    pybliometrics.sciencedirect.init(
        config_path="/project/pybliometrics.cfg",
        keys=[settings.SCOPUS_API_KEY],
        inst_tokens=[settings.SCOPUS_INSTITUTION_KEY],
    )
    publications = []
    for query in PublicationQuery.objects.filter(
        source_type=RawPublication.SCIENCE_DIRECT
    ):
        search = ScienceDirectSearch(query.query)
        if not search.results:
            logger.info(f"No results for Science Direct query: {query.query}")
            continue
        for i, raw_pub in enumerate(search.results):
            try:
                update_progress(
                    stage=0, current=i, total=len(search.results), task=task
                )

                title = utils.decode_unicode_text(raw_pub.title)
                published_on = datetime.datetime.strptime(raw_pub.coverDate, "%Y-%m-%d")
                year = published_on.year
                # get the author names with decoded unicode characters
                author_names = utils.decode_unicode_text(raw_pub.authors)
                # authors as a list of strings "firstname lastname" format
                authors = [
                    utils.format_author_name(author)
                    for author in author_names.split(";")
                ]
                doi = raw_pub.doi if raw_pub.doi else ""
                link = ""
                if doi:
                    link = f"https://www.doi.org/{doi}"
                pub_model = Publication(
                    title=title,
                    year=year,
                    month=published_on.month,
                    author=" and ".join(authors),
                    # Science Direct only indexes journal articles
                    publication_type="journal article",
                    bibtex_source="{}",
                    added_by_username="admin",
                    forum=raw_pub.publicationName,
                    doi=doi,
                    link=link,
                    status=Publication.STATUS_SUBMITTED,
                )
                logger.info(
                    f"Processing publication {raw_pub.pii} - {title} - {query.query}"
                )
                publications.append(
                    RawPublicationSource(
                        pub_model=pub_model,
                        source_id=raw_pub.pii,
                        source_name=RawPublication.SCIENCE_DIRECT,
                        cites_chameleon_pub=None,
                        found_with_query=query,
                    )
                )
            except Exception as e:
                # TODO  we keep hitting this
                logger.error(f"Error processing publication {raw_pub.pii}: {e}")
                logger.exception(e)
                continue
    return publications
