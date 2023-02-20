import datetime
import logging
import re

from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from requests import ReadTimeout

from projects.models import ChameleonPublication, Publication
from projects.user_publication import utils

logger = logging.getLogger("projects")

CHAMELEON_QUERY = (
    "( TITLE (chameleon) OR REF (chameleon) OR ABS (chameleon) OR KEY (chameleon) )"
    "AND PUBYEAR > 2014 AND SUBJAREA(COMP)"
)

CHAMELEON_REFS_REGEX = [
    re.compile(pattern)
    for pattern in [
        "chameleon:(.*)testbed for computer science research",
        "lessons learned from(.*)chameleon testbed",
        "chameleon cloud testbed(.*)software defined networking",
        "chameleoncloud.org",
    ]
]


def _get_references(a):
    return a.references if a.references else []


def _parse_author(author):
    names = [name.strip() for name in author.split(",")]
    if len(names) > 1:
        return f"{names[1]} {names[0]}"
    else:
        return names[0]


def _get_pub_type(scopus_pub_type):
    if scopus_pub_type == "Conference Paper":
        return "conference full paper"
    if scopus_pub_type == "Article" or scopus_pub_type == "Review":
        return "journal article"
    return scopus_pub_type


def _publication_references_chameleon(references):
    for ref in references:
        ref_title = ref.title.lower() if ref.title else ""
        ref_fulltext = ref.fulltext.lower() if ref.fulltext else ""
        for cref_regex in CHAMELEON_REFS_REGEX:
            if cref_regex.search(ref_title) or cref_regex.search(ref_fulltext):
                return True


def pub_import(dry_run=True):
    search = ScopusSearch(CHAMELEON_QUERY)
    logger.debug("Performed search")
    publications = []
    for raw_pub in search.results:
        logger.debug(f"Fetching results for {raw_pub.eid}")
        retries = 0
        references = None
        while retries < 5:
            try:
                references = _get_references(AbstractRetrieval(raw_pub.eid, view="REF"))
                break
            except ReadTimeout:
                msg = f"Failed abstract retrieval for {raw_pub.eid}."
                if retries < 5:
                    logger.warning(msg + " Retrying.")
                else:
                    logger.error(msg)
            retries += 1
        # If we retried 5 times to fetch references,
        # then consider the publication a lost cause
        if not references:
            continue

        if not _publication_references_chameleon(references):
            continue

        title = utils.decode_unicode_text(raw_pub.title)
        published_on = datetime.datetime.strptime(raw_pub.coverDate, "%Y-%m-%d")
        year = published_on.year
        author_names = utils.decode_unicode_text(raw_pub.author_names)
        authors = [_parse_author(author) for author in author_names.split(";")]
        proj = utils.guess_project_for_publication(authors, year)
        if not proj:
            continue

        if (
            not proj
            or ChameleonPublication.objects.filter(title__iexact=title).exists()
            or Publication.objects.filter(title=title, project_id=proj).exists()
        ):
            continue

        pub_model = Publication(
            title=title,
            year=year,
            month=published_on.month,
            author=" and ".join(authors),
            entry_created_date=datetime.date.today(),
            project=proj,
            publication_type=_get_pub_type(raw_pub.subtypeDescription),
            bibtex_source="{}",
            added_by_username="admin",
            forum=raw_pub.publicationName,
            doi=raw_pub.doi,
            link=f"https://www.doi.org/{raw_pub.doi}" if raw_pub.doi else None,
            source="scopus",
            status=Publication.STATUS_IMPORTED,
        )
        publications.append(pub_model)
        if dry_run:
            logger.info(f"import {str(pub_model)}")
    return publications
