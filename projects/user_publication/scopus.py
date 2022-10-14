import datetime
import logging
from pybliometrics.scopus import ScopusSearch
from pybliometrics.scopus import AbstractRetrieval
from pybliometrics.scopus import AuthorSearch
import re

from projects.models import Publication
from projects.user_publication import utils

logger = logging.getLogger("projects")

CHAMELEON_QUERY = (
    "( TITLE (chameleon) OR REF (chameleon) OR ABS (chameleon) OR KEY (chameleon) )"
    "AND PUBYEAR > 2014 AND SUBJAREA(COMP)"
)

CHAMELEON_REFS = [
    "chameleon:(.*)testbed for computer science research",
    "lessons learned from(.*)chameleon testbed",
    "chameleon cloud testbed(.*)software defined networking",
    "chameleoncloud.org",
]


def _get_references(a):
    return a.references if a.references else []


def _parse_authors(author_ids):
    author_keys = []
    for aid in author_ids:
        a = AuthorSearch(f"AU-ID({aid})")
        author = a.authors[0]
        author_keys.append((author.givenname.lower()[0] + ".", author.surname.lower()))
    return author_keys


def _get_pub_type(scopus_pub_type):
    if scopus_pub_type == "Conference Paper":
        return "conference full paper"
    if scopus_pub_type == "Article" or scopus_pub_type == "Review":
        return "journal article"
    return scopus_pub_type


def pub_import(dry_run=True):
    pi_projects = utils.get_pi_projects()
    all_publications = utils.get_publications()

    search = ScopusSearch(CHAMELEON_QUERY)
    for r in search.results:
        references = _get_references(AbstractRetrieval(r.eid, view="REF"))
        is_chameleon_paper = False
        for ref in references:
            ref_title = ref.title.lower() if ref.title else ""
            ref_fulltext = ref.fulltext.lower() if ref.fulltext else ""
            for cref_regex in CHAMELEON_REFS:
                if re.search(cref_regex, ref_title) or re.search(
                    cref_regex, ref_fulltext
                ):
                    is_chameleon_paper = True
                    break
        if is_chameleon_paper:
            title = r.title
            published_on = datetime.datetime.strptime(r.coverDate, "%Y-%m-%d")
            year = published_on.year
            authors = _parse_authors(r.author_ids.split(";"))
            proj = utils.link_publication_to_project(pi_projects, authors, year)
            project_id = proj[0]

            if (
                project_id
                and title.lower() not in utils.CHAMELEON_PUBLICATIONS
                and not utils.pub_exists(all_publications, title, project_id)
            ):
                pub = Publication()

                pub.title = title
                pub.year = year
                pub.month = published_on.month
                pub.author = r.author_names.replace(";", " and ")
                pub.entry_created_date = datetime.date.today().strftime("%Y-%m-%d")
                pub.project_id = project_id
                pub.publication_type = _get_pub_type(r.subtypeDescription)
                pub.bibtex_source = "{}"
                pub.added_by_username = "admin"
                pub.forum = r.publicationName
                pub.doi = r.doi
                if pub.doi:
                    pub.link = f"https://www.doi.org/{pub.doi}"
                pub.source = "scopus"
                pub.status = Publication.STATUS_IMPORTED

                if dry_run:
                    logger.info(f"import {str(pub)}")
                else:
                    pub.save()
