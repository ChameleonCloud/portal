import datetime
import logging
import re

from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from requests import ReadTimeout

from projects.models import ChameleonPublication, Project, Publication, PublicationSource

from projects.user_publication import utils
from projects.user_publication.utils import PublicationUtils
from projects.user_publication.deduplicate import flag_duplicates

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
            print(raw_pub.title, "Does not referece chameleon")
            continue
        title = utils.decode_unicode_text(raw_pub.title)
        published_on = datetime.datetime.strptime(raw_pub.coverDate, "%Y-%m-%d")
        year = published_on.year
        # get the author names with decoded unicode charachters
        author_names = utils.decode_unicode_text(raw_pub.author_names)
        # authors as a list of strings "firstname lastname" format
        authors = [utils.format_author_name(author) for author in author_names.split(";")]
        pub_model = Publication(
            title=title,
            year=year,
            month=published_on.month,
            author=" and ".join(authors),
            publication_type=PublicationUtils.get_pub_type({
                "ENTRYTYPE": raw_pub.subtypeDescription
            }),
            bibtex_source="{}",
            added_by_username="admin",
            forum=raw_pub.publicationName,
            doi=raw_pub.doi,
            link=f"https://www.doi.org/{raw_pub.doi}" if raw_pub.doi else None,
            status=Publication.STATUS_SUBMITTED
        )
        # all the projects from the authors in chameleon
        projects = PublicationUtils.get_projects_for_author_names(authors, year)
        # valid projects that are active prior to the publication year
        valid_projects = []
        for project_code in projects:
            try:
                project = Project.objects.get(charge_code=project_code)
            except Project.DoesNotExist:
                logger.info(f"{project_code} does not exist in database")
                continue
            if utils.is_project_prior_to_publication(project, year):
                valid_projects.append(project_code)
        author_usernames = [utils.get_usernames_for_author(author) for author in authors]
        report_file_name = 'scoppu_report.csv'
        if (
            not valid_projects
            or ChameleonPublication.objects.filter(title__iexact=title).exists()
        ):
            reason = "Skipping: no valid projects"
            utils.export_publication_csv(
                report_file_name,
                pub_model,
                PublicationSource.SCOPUS,
                author_usernames,
                valid_projects,
                projects,
                reason
            )
            continue
        same_pubs = utils.publications_with_same_attributes(pub_model, Publication.objects)
        reason = None
        if len(same_pubs) > 0:
            same_pubs_ids_str = ""
            for same_pub in same_pubs:
                same_pubs_ids_str += f"{same_pub.id} "
                utils.add_source_to_pub(same_pub, PublicationSource.SCOPUS, dry_run=dry_run)
            logger.info("Found publication with same attributes - adding source")
            reason = f"Adding Source: Found Publication ids {same_pubs_ids_str} with same attributes"
            utils.export_publication_csv(
                report_file_name,
                pub_model,
                PublicationSource.SCOPUS,
                author_usernames,
                valid_projects,
                projects,
                reason
            )
            continue
        duplicates = flag_duplicates(PublicationSource.SCOPUS, dry_run=dry_run, pub_model=pub_model)
        if pub_model.status == Publication.STATUS_DUPLICATE:
            logger.info("Found publication as duplicate. Run review_duplicates() to review")
            reason = f"Skipping: Found Duplicate {duplicates[pub_model.title]}"
            utils.export_publication_csv(
                report_file_name,
                pub_model,
                PublicationSource.SCOPUS,
                author_usernames,
                valid_projects,
                projects,
                reason
            )
            continue
        if not dry_run:
            # save publication model with source
            utils.save_publication(pub_model, PublicationSource.SCOPUS)
            reason = f"Saving: {pub_model.title}"
            utils.export_publication_csv(
                report_file_name,
                pub_model,
                PublicationSource.SCOPUS,
                author_usernames,
                valid_projects,
                projects,
                reason
            )
        logger.info(f"import {str(pub_model)}")
        publications.append(pub_model)
    return publications
