import logging
from datetime import date

from projects.models import (
    ChameleonPublication,
    Project,
    Publication,
    PublicationSource,
)
from projects.user_publication import gscholar, scopus, semantic_scholar, utils
from projects.user_publication.deduplicate import get_originals_for_duplicate_pub
from projects.user_publication.utils import PublicationUtils
from django.db import transaction

logger = logging.getLogger(__name__)


def import_pubs(dry_run=True, source="all"):
    """Invoke import_pubs() interactively in django manage.py shell

    Args:
        dry_run (bool, optional): False means stores the publications in DB. Defaults to True.
        source (str, optional): scopus, semantic_scholar, gscholar as options. Defaults to "all".
    """
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
        same_pubs = utils.get_publications_with_same_attributes(pub, Publication)
        if same_pubs.exists():
            for same_pub in same_pubs:
                utils.add_source_to_pub(same_pub, source)
            continue
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
        report_file_name = f"publications_run_{date.today()}_{source}.csv"

        pubs_to_check_against = Publication.objects.filter(year=pub.year).order_by(
            "-id"
        )
        original_pubs = get_originals_for_duplicate_pub(pub, pubs_to_check_against)

        # Check if there are valid projects and if the publication already exists
        if (
            not valid_projects
            or ChameleonPublication.objects.filter(title__iexact=pub.title).exists()
        ):
            reason_for_report = "Skipping: no valid projects"

        # If all conditions are met, import the publication
        else:
            if pub.status == Publication.STATUS_DUPLICATE:
                logger.info(
                    "Found publication as duplicate. Run review_duplicates() to review"
                )
                reason_for_report = f"Saving: Found Duplicates of {original_pubs}"
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
    print("4. If the publication did not use chameleon")
    print("5. To leave the status as is. Choose this")
    inp = input("Choose 1, 2, 3 or 4: ")
    if inp == "1":
        return PublicationSource.APPROVED_WITH_PUBLICATION
    elif inp == "2":
        return PublicationSource.APPROVED_WITH_JUSTIFICATION
    elif inp == "3":
        return PublicationSource.APPROVED_WITH_EMAIL
    elif inp == "4":
        return 
    elif inp == "5":
        return PublicationSource.APPROVED_WITH_PENDING_REVIEW
    else:
        return choose_approved_with_option()


def choose_email_approval_status():
    print("Change the status of approving the publication with email")
    print("1. If attestation is received")
    print("2. If rejected")
    print("3. To leave as is, no reply yet from the user")
    inp = input("Choose 1, 2, 3: ")
    if inp == "1":
        return 'approved'
    elif inp == "2":
        return 'rejected'
    elif inp == "3":
        return
    else:
        return choose_email_approval_status()


def update_status_for_email_approval(pub, user_reported_source):
    email_choice = choose_email_approval_status()
    if email_choice == 'approved':
        with transaction.atomic():
            user_reported_source.approved_with = PublicationSource.APPROVED_WITH_EMAIL
            pub.status = Publication.STATUS_APPROVED
            pub.reviewed = True
            pub.save()
            user_reported_source.save()
    elif email_choice == 'rejected':
        with transaction.atomic():
            user_reported_source.approved_with = PublicationSource.APPROVED_WITH_EMAIL
            pub.status = Publication.STATUS_REJECTED
            pub.reviewed = True
            pub.save()
            user_reported_source.save()
    else:
        with transaction.atomic():
            user_reported_source.approved_with = PublicationSource.APPROVED_WITH_PENDING_REVIEW
            pub.reviewed = False
            pub.save()
            user_reported_source.save()


def update_user_reported_status(pub, user_reported_source):
    print("Choose the appropriate approval for user reported source")
    choice = choose_approved_with_option()
    # For email approval
    if choice and choice == PublicationSource.APPROVED_WITH_EMAIL:
        update_status_for_email_approval(pub, user_reported_source)
    # for other approvals
    elif choice:
        with transaction.atomic():
            user_reported_source.status = choice
            user_reported_source.save()
            if choice == PublicationSource.APPROVED_WITH_PENDING_REVIEW:
                pub.reviewed = False
                pub.status = Publication.STATUS_SUBMITTED
            else:
                pub.reviewed = True
                pub.status = Publication.STATUS_APPROVED
            pub.save()
    # if rejected
    else:
        with transaction.atomic():
            pub.reviewed = True
            pub.status = Publication.STATUS_REJECTED
            pub.save()


def update_other_sources_status(pub, sources):
    print("Choose the appropriate approval for other sources")
    for source in sources:
        print(f"{source.__repr__()}\n")
    choice = choose_approved_with_option()
    if choice:
        for source in sources:
            with transaction.atomic():
                source.approved_with = choice
                source.save()
                print(f"status updated to {source.approved_with}")
        if choice != PublicationSource.APPROVED_WITH_PENDING_REVIEW:
            with transaction.atomic():
                pub.reviewed = True
                pub.status = Publication.STATUS_APPROVED
                pub.save()
    else:
        with transaction.atomic():
            pub.status = Publication.STATUS_REJECTED
            pub.reviewed = True
            pub.save()


def review_imported_publications():
    """This needs be to be invoked interactively
    with functionality to review imported publications
    go through all the flagged duplicates that are pending a review
    """
    pubs_to_review = Publication.objects.filter(
        status=Publication.STATUS_SUBMITTED, reviewed=False
    )
    pubs_count = pubs_to_review.count()
    print("Found publications to review: {pubs_count}")
    review_counter = 0
    for pub in pubs_to_review:
        review_counter += 1
        print(f"Publication to review {review_counter} of {pubs_count}")
        print(f"Publication: \n {pub.__repr__()}\n")
        for source in pub.sources.all():
            print(f"with source: {source.__repr__()}\n")
        approval_needed_sources = pub.sources.filter(
            approved_with=PublicationSource.APPROVED_WITH_PENDING_REVIEW
        ).exclude(name=PublicationSource.USER_REPORTED)
        user_reported_source = pub.sources.filter(
            name=PublicationSource.USER_REPORTED,
        ).first()
        if user_reported_source:
            if user_reported_source.approved_with == PublicationSource.APPROVED_WITH_PENDING_REVIEW:
                update_user_reported_status(pub, user_reported_source)
            # update other sources to same approved status of user_reported source
            with transaction.atomic():
                for other_source in approval_needed_sources:
                    other_source.approved_with = user_reported_source.approved_with
                    other_source.save()

        elif approval_needed_sources:
            print("These sources need review: ")
            update_other_sources_status(pub, approval_needed_sources)
        if pub.sources.filter(
            approved_with=PublicationSource.APPROVED_WITH_PENDING_REVIEW
        ).exists():
            continue
        else:
            print("All sources are reviewed")
            if pub.reviewed:
                print("Publication is reviewed")
            else:
                print("Publication: \n", pub.__repr__())
                for source in pub.sources.all():
                    print("with source: ", source.__repr__())
                    print("")
                if pub.status == Publication.STATUS_APPROVED:
                    pub.reviewed = True
                    pub.save()
                else:
                    print("Publication is marked not reviewed")
                    inp = input("Mark publication as reviewed? y/n: ")
                    if inp == 'y':
                        pub.status = Publication.STATUS_APPROVED
                        pub.reviewed = True
                        pub.save()
                    else:
                        print("Publication is marked as not reviewed. Run review_publications() to review")
