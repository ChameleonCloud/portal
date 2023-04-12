# Functions to identify similarities in two publications to flag one of them as diplicate

import logging

from django.db import transaction

from projects.models import Publication, PublicationDuplicate
from projects.user_publication.utils import PublicationUtils, update_original_pub_source

logger = logging.getLogger(__name__)


def get_originals_for_duplicate_pub(dpub, pubs_to_check_against):
    """Returns original pubs that are almost same as dpub

    Args:
        dpub (projects.models.Publication): pub to check if it is similar to
        pubs_to_check_against (list): list of pubs to check against

    Returns:
        list: original publications that are similar to dpub
    """
    original_pubs = []
    # Loop through each subset publication to check against for duplicates
    for pub2 in pubs_to_check_against:
        # Check if dpub and pub2 are similar enough to be flagged as duplicates
        if PublicationUtils.is_pub_similar(dpub, pub2):
            dpub.status = Publication.STATUS_DUPLICATE
            original_pubs.append(pub2)
            # Log the publications that have been flagged as duplicates
            logger.info(
                f"{dpub.title} is flagged duplicate to {pub2.id} {pub2.title}"
            )
    return original_pubs


def get_duplicate_pubs(pubs=None):
    """
    returns duplicate publications in the database.
    If passed pubs are not stored in database - this does not work.
    Use get_originals_for_duplicate_pub() for each publication

    Args:
        pubs (list, optional): list of Publication models to check if it is a duplicate.
            Defaults to None, checks for all the publications if None
    Returns:
        (dict): keys are publication that is found as duplicate values are list of original publications
    """
    # return a mapping of flagged duplicates and their original publications
    duplicate_with_their_original_pubs_map = {}

    # Get a list of publications to check for duplicates
    if pubs:
        pubs_to_check_duplicates = pubs
    else:
        # get the publications in reverse so latest can be checked against old ones
        # reviewed=False are the ones that are yet to be reviewed
        pubs_to_check_duplicates = Publication.objects.filter(reviewed=False).order_by(
            "-id"
        )

    # Loop through each publication to check for duplicates
    for pub1 in pubs_to_check_duplicates:
        # Get a subset of publications with id less than the publication at question
        # and of same year as the publication at question to check against
        if not pub1.year:
            logger.info(f"{pub1.title} does not have year - ignoring")
            continue
        # publications without ID means they are not in the database yet. So get all Publications
        # that are older than pub1
        pubs_to_check_against = Publication.objects.filter(
            id__lt=pub1.id, year=pub1.year
        ).order_by("-id")

        duplicate_with_their_original_pubs_map[pub1] = get_originals_for_duplicate_pub(
            pub1, pubs_to_check_against
        )
    return duplicate_with_their_original_pubs_map


def flag_duplicate_in_whole_db():
    """Run this interactively to flag duplicates - change status to Duplicate
    for publication in whole database
    """
    pubs = Publication.objects.all()
    duplicates = get_duplicate_pubs(pubs)
    for pub in pubs:
        if pub in duplicates:
            with transaction.atomic():
                pub.status = Publication.STATUS_DUPLICATE
                pub.reviewed = False
                pub.save()


def review_duplicates(dry_run=True):
    """This function needs to be invoked interactively through cli
    Prompts reviewer to review publications that are flagged as duplicates (y/n)

    Args:
        dry_run (bool, optional):
    """
    duplicate_originals_map = get_duplicate_pubs()
    # go through all the flagged duplicates that are pending a review
    total_dupes = len(duplicate_originals_map)
    print(f"Found total {total_dupes} publications duplicate")
    count = 0
    for dpub in duplicate_originals_map:
        count += 1
        opubs = duplicate_originals_map[dpub]
        for opub in opubs:
            print(f"Found duplicate publication: {count}/{total_dupes}")
            print(f"Publication 1: \n {dpub.__repr__()}\n")
            print(f"Publication 2: \n {opub.__repr__()}\n")
            is_duplicate = input(
                "Is Publication 1 a duplicate? (y/n/c): use 'c' to cancel:"
            )
            print()
            with transaction.atomic():
                if is_duplicate == "n":
                    dpub.status = Publication.STATUS_SUBMITTED
                elif is_duplicate == "y":
                    update_original_pub_source(opub, dpub)
                    PublicationDuplicate.objects.create(
                        duplicate=dpub,
                        original=opub
                    )
                else:
                    continue
                dpub.reviewed = False
                dpub.save()
