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
            original_pubs.append(pub2)
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


def pick_duplicate_from_pubs(dpub, opub):
    # this logic can further extend, currently its for if publication is preprint
    preprint_in_duplicate = (
        'preprint' in dpub.forum if dpub.forum else ""
        or 'preprint' in dpub.bibtex_source
        or 'arXiv' in dpub.doi if dpub.doi else ""
        or 'preprint' in dpub.publication_type
    )
    preprint_in_original = (
        'preprint' in opub.forum if opub.forum else ""
        or 'preprint' in opub.bibtex_source
        or 'arXiv' in opub.doi if opub.doi else ""
        or 'preprint' in opub.publication_type
    )
    if preprint_in_duplicate or preprint_in_original:
        # if preprint is both in duplicate and original pick duplicate as duplicate
        if preprint_in_duplicate and preprint_in_original:
            duplicate_pub = dpub
            original_pub = opub
        elif preprint_in_duplicate:
            duplicate_pub = dpub
            original_pub = opub
        else:
            duplicate_pub = opub
            original_pub = dpub
    else:
        duplicate_pub = dpub
        original_pub = opub
    return duplicate_pub, original_pub


def review_duplicates(dry_run=True):
    """This function needs to be invoked interactively through cli
    Prompts reviewer to review publications that are flagged as duplicates (y/n)

    Args:
        dry_run (bool, optional):
    """
    # get all the publications that are to be checked for duplicates
    pubs_to_check_for_duplicates = Publication.objects.filter(
        checked_for_duplicates=False
    ).order_by("id")
    print(f"{len(pubs_to_check_for_duplicates)} pubs to check for duplicates")
    pub_checked = 0
    for pub1 in pubs_to_check_for_duplicates:
        pub_checked += 1
        # get all the publications that already checked for duplicates
        # and are not duplicates, that are published in the same year as pub1
        # and is older than (created) pub1
        pubs_to_check_against = Publication.objects.filter(
            year=pub1.year, id__lt=pub1.id, checked_for_duplicates=True
        ).exclude(status=Publication.STATUS_DUPLICATE).order_by("id")
        original_pubs = get_originals_for_duplicate_pub(pub1, pubs_to_check_against)
        # is not a duplicate pub
        if len(original_pubs) == 0:
            if not dry_run:
                with transaction.atomic():
                    pub1.checked_for_duplicates = True
                    pub1.save()
            continue
        for opub in original_pubs:
            print(f"\nChecking publication: {pub_checked} count out of {len(pubs_to_check_for_duplicates)}")
            print(f"Publication 1: \n {pub1.__repr__()}\n")
            print(f"Publication 2: \n {opub.__repr__()}\n")

            print("\nAuthors")
            print(f"{pub1.author}")
            print(f"{opub.author}")
            print("\nForum")
            print(f"{pub1.forum}")
            print(f"{opub.forum}")
            is_duplicate = input(
                "Is Publication 1 a duplicate? (y/n/c): use 'c' to cancel:"
            )
            print()
            if dry_run:
                continue
            with transaction.atomic():
                if is_duplicate == "n":
                    pub1.checked_for_duplicates = True
                elif is_duplicate == "y":
                    duplicate_pub, original_pub = pick_duplicate_from_pubs(pub1, opub)
                    duplicate_pub.status = Publication.STATUS_DUPLICATE
                    update_original_pub_source(original_pub, duplicate_pub)
                    PublicationDuplicate.objects.create(
                        duplicate=duplicate_pub,
                        original=original_pub
                    )
                    # Log the publications that have been flagged as duplicates
                    logger.info(
                        f"{duplicate_pub.title} is flagged duplicate to {original_pub.id} {original_pub.title}"
                    )
                else:
                    continue
                pub1.checked_for_duplicates = True
                pub1.save()
