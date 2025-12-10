# Contains functions to import publications for various sources
# Also contains functions to review imported publications

import logging
from datetime import date

from projects.models import (
    ChameleonPublication,
    Project,
    Publication,
    RawPublication,
)
from projects.user_publication import gscholar, scopus, semantic_scholar, utils
from projects.user_publication.utils import PublicationUtils, update_progress
from django.db import transaction
from celery.decorators import task

LOG = logging.getLogger(__name__)


@task(bind=True)
def import_pubs_scopus_task(self):
    return import_pubs_task(self, "scopus")


@task(bind=True)
def import_pubs_semantic_scholar_task(self):
    return import_pubs_task(self, "semantic_scholar")


@task(bind=True)
def import_pubs_google_scholar_task(self):
    return import_pubs_task(self, "gscholar")


def import_pubs_task(self, source):
    LOG.info("Importing publications")
    try:
        import_pubs(self, dry_run=False, source=source)
    except Exception as e:
        self.update_state(state="ERROR")
        LOG.error(f"Error importing {source} publications: {type(e)} {e}")
        raise
    return "Completed"


def import_pubs(task, dry_run=True, source="all"):
    """Invoke import_pubs() interactively in django manage.py shell

    Args:
        dry_run (bool, optional): False means stores the publications in DB. Defaults to True.
        source (str, optional): scopus, semantic_scholar, gscholar as options. Defaults to "all".
    """
    pubs = []

    # Import publications from different sources based on the input argument
    if source in ["scopus", "all"]:
        pubs.extend(scopus.pub_import(task, dry_run))
    if source in ["semantic_scholar", "all"]:
        pubs.extend(semantic_scholar.pub_import(task, dry_run))
    if source in ["gscholar", "all"]:
        pubs.extend(gscholar.pub_import(task, dry_run))

    # Process each found publication
    for i, raw_pub in enumerate(pubs):
        report_file_name = f"publications_run_{date.today()}_{raw_pub.source_name}.csv"
        try:
            update_progress(stage=1, current=i, total=len(pubs), task=task)
            # get matching pubs in DB, add this as a source, continue to next new pub.
            same_pubs = utils.get_publications_with_same_attributes(
                raw_pub.pub_model, Publication
            )
            if same_pubs.exists():
                for same_pub in same_pubs:
                    utils.add_source_to_pub(same_pub, raw_pub)
                continue

            # If all conditions are met, import the publication
            else:
                LOG.info(f"import {raw_pub.pub_model.__repr__()}")
                reason_for_report = f"Saving: {raw_pub.pub_model.title}"
                # Save the publication if it is not a dry run
                if not dry_run:
                    utils.save_publication(raw_pub)

            # Export the publication status report
            utils.export_publication_status_run(
                report_file_name,
                raw_pub.pub_model,
                None,
                None,
                None,
                reason_for_report,
            )
        except Exception as e:
            LOG.error(
                f"Error processing publication {raw_pub.pub_model.title} from {source}"
            )
            LOG.exception(e)
            continue


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
        return RawPublication.APPROVED_WITH_PUBLICATION
    elif inp == "2":
        return RawPublication.APPROVED_WITH_JUSTIFICATION
    elif inp == "3":
        return RawPublication.APPROVED_WITH_EMAIL
    elif inp == "4":
        return
    elif inp == "5":
        return "DO NOTHING"
    else:
        return choose_approved_with_option()


def update_other_sources_status(pub, sources):
    print("Choose the appropriate approval for other sources")
    for source in sources:
        print(f"{source.__repr__()}\n")
    choice = choose_approved_with_option()
    if choice:
        if choice != "DO NOTHING":
            with transaction.atomic():
                pub.status = Publication.STATUS_APPROVED
                pub.save()
                for source in pub.sources.all():
                    source.approved_with = choice
                    source.cites_chameleon = True
                    source.save()
    else:
        with transaction.atomic():
            pub.status = Publication.STATUS_REJECTED
            pub.save()


def review_imported_publications():
    """This needs be to be invoked interactively
    with functionality to review imported publications
    go through all the flagged duplicates that are pending a review
    """
    pubs_to_review = Publication.objects.filter(
        status=Publication.STATUS_SUBMITTED
    ).order_by("id")
    pubs_count = pubs_to_review.count()
    print("Found publications to review: {pubs_count}")
    review_counter = 0
    for pub in pubs_to_review:
        review_counter += 1
        print(f"Publication to review {review_counter} of {pubs_count}")
        print(f"Publication: {pub.id} \n {pub.__repr__()}\n")
        for source in pub.sources.all():
            print(f"with source: {source.__repr__()}\n")
        approval_needed_sources = pub.sources.filter(
            approved_with__isnull=True
        ).exclude(name=RawPublication.USER_REPORTED)
        user_reported_source = pub.sources.filter(
            name=RawPublication.USER_REPORTED,
        ).first()
        if user_reported_source:
            # update other sources as approved with same method
            # as the user_reported approved_with
            if user_reported_source.approved_with:
                with transaction.atomic():
                    for other_source in approval_needed_sources:
                        other_source.approved_with = user_reported_source.approved_with
                        other_source.save()
            else:
                print("User reported publications can be approved from admin interface")
                print("Skipping publication...")
        elif approval_needed_sources:
            print("These sources need review: ")
            update_other_sources_status(pub, approval_needed_sources)
        # if the publication sources are not approved yet, move to next publication
        if pub.sources.filter(approved_with__isnull=True).exists():
            continue
        else:
            print("All sources are reviewed")
            if pub.status in [Publication.STATUS_APPROVED, Publication.STATUS_REJECTED]:
                print("Publication is reviewed")
            else:
                print("Publication is not reviewed: \n", pub.__repr__())
                with transaction.atomic():
                    for source in pub.sources.all():
                        print("with source: ", source.__repr__())
                        print("")
                        source.approved_with = None
                        source.save()
