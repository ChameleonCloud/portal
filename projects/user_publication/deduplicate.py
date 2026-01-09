# Functions to identify similarities in two publications to flag one of them as diplicate

import logging

from projects.models import Publication
from projects.user_publication.utils import PublicationUtils

logger = logging.getLogger(__name__)


def get_originals_for_duplicate_pub(dpub):
    """Returns original pubs that are almost same as dpub

    Args:
        dpub (projects.models.Publication): pub to check if it is similar to
        pubs_to_check_against (list): list of pubs to check against

    Returns:
        list: original publications that are similar to dpub
    """
    pubs_to_check_against = (
        Publication.objects.filter(checked_for_duplicates=True)
        .exclude(id=dpub.id)
        .exclude(status="DUPLICATE")
        .order_by("id")
    )

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
    If the passed pubs are not stored (saved) in the database
    the function fails with an error, as it needs ID of the publication
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
        # checked_for_duplicates=False are the ones that are yet to be reviewed
        pubs_to_check_duplicates = Publication.objects.filter(
            checked_for_duplicates=False
        ).order_by("-id")

    # Loop through each publication to check for duplicates
    for pub1 in pubs_to_check_duplicates:
        # Get a subset of publications with id less than the publication at question
        # and of same year as the publication at question to check against
        if not pub1.year:
            logger.info(f"{pub1.title} does not have year - ignoring")
            continue
        # Get all Publications that are older than pub1
        duplicate_with_their_original_pubs_map[pub1] = get_originals_for_duplicate_pub(
            pub1
        )
    return duplicate_with_their_original_pubs_map
