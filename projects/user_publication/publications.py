import logging
from datetime import date

from projects.models import (ChameleonPublication, Project, Publication,
                             PublicationSource)
from projects.user_publication import gscholar, scopus, semantic_scholar, utils
from projects.user_publication.deduplicate import flag_duplicates
from projects.user_publication.utils import PublicationUtils

logger = logging.getLogger(__name__)


def import_pubs(dry_run=True, file_name="", source="all"):
    pubs = []

    # Import publications from different sources based on the input argument
    if source in ["scopus", "all"]:
        pubs.extend(scopus.pub_import(dry_run))
    if source in ["semantic_scholar", "all"]:
        pubs.extend(semantic_scholar.pub_import(dry_run))
    if source in ["gscholar", "all"]:
        pubs.extend(gscholar.pub_import(dry_run))

    # Process each publication
    for source, pub in pubs:
        authors = [author.strip() for author in pub.author.split("and")]
        projects = PublicationUtils.get_projects_for_author_names(authors, pub.year)

        # Get valid projects that are active prior to the publication year
        valid_projects = []
        for project_code in projects:
            try:
                project = Project.objects.get(charge_code=project_code)
            except Project.DoesNotExist:
                logger.info(f"{project_code} does not exist in database")
                continue
            if utils.is_project_prior_to_publication(project, pub.year):
                valid_projects.append(project_code)

        author_usernames = [utils.get_usernames_for_author(author) for author in authors]
        report_file_name = f'publications_run_{date.today()}.csv'

        duplicates = flag_duplicates(pub_model=pub)

        # Check if there are valid projects and if the publication already exists
        if (
            not valid_projects
            or ChameleonPublication.objects.filter(title__iexact=pub.title).exists()
        ):
            reason_for_report = "Skipping: no valid projects"

        # Check if publication is marked as duplicate
        elif pub.status == Publication.STATUS_DUPLICATE:
            logger.info("Found publication as duplicate. Run review_duplicates() to review")
            reason_for_report = f"Skipping: Found Duplicates {duplicates[pub.title]}"

        # If all conditions are met, import the publication
        else:
            logger.info(f"import {pub.__repr__()}")
            reason_for_report = f"Saving: {pub.title}"
            # Save the publication if it is not a dry run
            if not dry_run:
                utils.save_publication(pub, source)

        # Export the publication status report
        utils.export_publication_status_run(
            report_file_name, pub, author_usernames,
            valid_projects, projects, reason_for_report
        )


def review_imported_publications():
    # with functionality to review imported publications
    pass