import logging
from datetime import date
from projects.user_publication.deduplicate import flag_duplicates
from projects.user_publication import scopus, semantic_scholar, gscholar, utils
from projects.user_publication.utils import export_publications, report_publications, PublicationUtils
from projects.models import Project, PublicationSource, ChameleonPublication, Publication

logger = logging.getLogger(__name__)


def import_pubs(dry_run=True, file_name="", source="all"):
    pubs = []
    if source in ["scopus", "all"]:
        pubs.extend(scopus.pub_import(dry_run))
    if source in ["semantic_scholar", "all"]:
        pubs.extend(semantic_scholar.pub_import(dry_run))
    if source in ["gscholar", "all"]:
        pubs.extend(gscholar.pub_import(dry_run))
    for pub in pubs:
        authors = [author.strip() for author in pub.author.split("and")]
        projects = PublicationUtils.get_projects_for_author_names(authors, pub.year)
        # valid projects that are active prior to the publication year
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
        duplicates = flag_duplicates(PublicationSource.SCOPUS, dry_run=dry_run, pub_model=pub)
        reason = None
        if (
            not valid_projects
            or ChameleonPublication.objects.filter(title__iexact=pub.title).exists()
        ):
            reason = "Skipping: no valid projects"
        elif pub.status == Publication.STATUS_DUPLICATE:
            logger.info("Found publication as duplicate. Run review_duplicates() to review")
            reason = f"Skipping: Found Duplicate {duplicates[pub.title]}"
        elif not dry_run:
            utils.save_publication(pub, PublicationSource.SCOPUS)
            reason = f"Saving: {pub.title}"
        utils.export_publication_status_run(
            report_file_name,
            pub,
            author_usernames,
            valid_projects,
            projects,
            reason
        )
        logger.info(f"import {str(pub)}")
