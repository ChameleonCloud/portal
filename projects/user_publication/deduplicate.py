# Functions to identify similarities in two publications to flag one of them as diplicate

import logging
from collections import defaultdict

from django.db import transaction

from projects.models import Publication
from projects.user_publication.utils import PublicationUtils, update_original_pub_source

logger = logging.getLogger(__name__)


def get_duplicate_pubs(pubs=None):
    """
    returns duplicate publications in the database.

    Args:
        pubs (list, optional): list of Publication models to check if it is a duplicate.
            Defaults to None, checks for all the publications if None
    Returns:
        (dict): keys are publication that is found as duplicate values are list of original publications
    """
    # return a mapping of flagged duplicates and their original publications
    duplicate_with_their_original_pubs_map = defaultdict(list)

    # Get a list of publications to check for duplicates
    if pubs:
        pubs_to_check_duplicates = pubs
    else:
        # get the publications in reverse so latest can be checked against old ones
        # reviewed=True are the ones that are reviewed and are concrete non-duplicates
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
        if not pub1.id:
            pubs_to_check_against = Publication.objects.filter(year=pub1.year).order_by(
                "-id"
            )
        else:
            pubs_to_check_against = Publication.objects.filter(
                id__lt=pub1.id, year=pub1.year
            ).order_by("-id")

        # Loop through each subset publication to check against for duplicates
        for pub2 in pubs_to_check_against:
            # Check if pub1 and pub2 are similar enough to be flagged as duplicates
            if PublicationUtils.is_pub_similar(pub1, pub2):
                pub1.status = Publication.STATUS_DUPLICATE
                duplicate_with_their_original_pubs_map[pub1].append(pub2)
                # Log the publications that have been flagged as duplicates
                logger.info(
                    f"{pub1.title} is flagged duplicate to {pub2.id} {pub2.title}"
                )
    return duplicate_with_their_original_pubs_map


def deduplicate_whole_db():
    """Run this interactively to flag duplicates - change status to Duplicate
    for publication in whole database
    """
    duplicates = get_duplicate_pubs()
    with transaction.atomic():
        for pub in duplicates:
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
    for dpub in duplicate_originals_map:
        opubs = duplicate_originals_map[dpub]
        for opub in opubs:
            print("Found duplicate publication: ")
            print("Publication 1: ", dpub.__repr__())
            print("Publication 2: ", opub.__repr__())
            print("Is publication ")
            is_duplicate = input(
                "Is Publication 1 a duplicate? (y/n/c): use 'c' to cancel"
            )
            with transaction.atomic():
                if is_duplicate == "n":
                    dpub.status = Publication.STATUS_APPROVED
                elif is_duplicate == "y":
                    update_original_pub_source(opub, dpub)
                    # as the publication is flagged as duplicate we can move on to next publication
                    break
                else:
                    continue
                dpub.reviewed = True
                dpub.save()
