import logging
from datetime import date

from projects.models import (
    ChameleonPublication,
    Project,
    Publication,
    PublicationSource,
)
from projects.user_publication import gscholar, scopus, semantic_scholar, utils
from projects.user_publication.deduplicate import get_duplicate_pubs
from projects.user_publication.utils import PublicationUtils
from django.db import transaction

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

        author_usernames = [
            utils.get_usernames_for_author(author) for author in authors
        ]
        report_file_name = f"publications_run_{date.today()}.csv"

        duplicates = get_duplicate_pubs(pubs=[pub])

        # Check if there are valid projects and if the publication already exists
        if (
            not valid_projects
            or ChameleonPublication.objects.filter(title__iexact=pub.title).exists()
        ):
            reason_for_report = "Skipping: no valid projects"

        # Check if publication is marked as duplicate
        elif pub.status == Publication.STATUS_DUPLICATE:
            logger.info(
                "Found publication as duplicate. Run review_duplicates() to review"
            )
            reason_for_report = f"Saving: Found Duplicates {duplicates[pub]}"

        # If all conditions are met, import the publication
        else:
            logger.info(f"import {pub.__repr__()}")
            reason_for_report = f"Saving: {pub.title}"
            # Save the publication if it is not a dry run
            if not dry_run:
                utils.save_publication(pub, source)

        # Export the publication status report
        utils.export_publication_status_run(
            report_file_name,
            pub,
            author_usernames,
            valid_projects,
            projects,
            reason_for_report,
        )


def choose_approved_with_option():
    print("Change the status of source's Approval status")
    print("1. If you have verified the publication was enabled by Chameleon")
    print("2. If the publication was uploaded as part of justification for a project")
    print(
        (
            "3. If the publication did not explicitly mention using Chameleon, "
            "send an email to authors and choose this option. "
            "if email is already sent then choose this option to input the confirmation"
        )
    )
    print("4. To leave the status as is. Choose this")
    inp = input("Choose 1, 2, 3 or 4")
    if inp == "1":
        return PublicationSource.APPROVED_WITH_PUBLICATION
    elif inp == "2":
        print("You chose two")
        return PublicationSource.APPROVED_WITH_JUSTIFICATION
    elif inp == "3":
        return PublicationSource.APPROVED_WITH_EMAIL
    elif inp == "4":
        return
    else:
        return choose_approved_with_option()


def review_imported_publications():
    """This needs be to be invoked interactively
    with functionality to review imported publications
    go through all the flagged duplicates that are pending a review
    """
    pubs_to_review = Publication.objects.filter(
        status=Publication.STATUS_SUBMITTED, reviewed=False
    )
    for pub in pubs_to_review:
        print("Found publication to review: ")
        print("Publication: ", pub.__repr__())
        for source in pub.sources.exclude(
            approved_with=PublicationSource.APPROVED_WITH_PENDING_REVIEW
        ):
            print("with source: ", source.__repr__())
        approval_needed_sources = pub.sources.filter(
            approved_with=PublicationSource.APPROVED_WITH_PENDING_REVIEW
        )
        if approval_needed_sources:
            print("These sources need review: ")
            for source in approval_needed_sources:
                print(source.__repr__())
                choice = choose_approved_with_option
                if choice:
                    if choice == PublicationSource.APPROVED_WITH_EMAIL:
                        print("")
                    with transaction.atomic():
                        source.approved_with = choice
                        source.save()
                        print(f"status updated to {source.approved_with}")
