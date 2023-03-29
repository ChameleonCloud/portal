# Functions to identify similarities in two publications to flag one of them as diplicate

from collections import defaultdict
import logging
from projects.user_publication.utils import PublicationUtils, update_original_pub_source
from projects.models import Publication, PublicationSource
from django.db.models import Q
from django.db import transaction

logger = logging.getLogger(__name__)


def flag_duplicates(pub_model=None):
    """
    flags duplicate publications in the database.
    When pub_model is supplied this model will be checked if it is a duplicate
    saves the model with status as DUPLICATE and if the pub_model is not already in database
    then the pub_model status is changed as DUPLICATE and lets downstream decide to save it or not

    Args:
        pub_model (models.Publication, optional): Publication model to check if it is a duplicate.
            Defaults to None, checks for all the publications if None
    Returns:
        (dict): keys are title or id (depends if the model is saved or not) of the publication
          that is flagged as duplicate values are ID of the original publication
    """
    # return a mapping of flagged duplicates and their original publications
    duplicate_mappings = defaultdict(list)

    # Get a list of publications to check for duplicates
    if pub_model:
        pubs_to_check_duplicates = [pub_model]
    else:
        # get the publications in reverse so latest can be checked against old ones
        # reviewed=True are the ones that are reviewed and are concrete non-duplicates
        pubs_to_check_duplicates = Publication.objects.filter(reviewed=False).order_by("-id")

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
            pub_key = pub1.title
            pubs_to_check_against = Publication.objects.filter(year=pub1.year).order_by('-id')
        else:
            pub_key = pub1.id
            pubs_to_check_against = Publication.objects.filter(id__lt=pub1.id, year=pub1.year).order_by('-id')

        # Loop through each subset publication to check against for duplicates
        for pub2 in pubs_to_check_against:
            # Check if pub1 and pub2 are similar enough to be flagged as duplicates
            if not PublicationUtils.is_pub_similar(pub1, pub2):
                continue
            pub1.status = Publication.STATUS_DUPLICATE
            duplicate_mappings[pub_key].append(pub2.id)
            # Log the publications that have been flagged as duplicates
            logger.info(f"{pub1.title} is flagged duplicate to {pub2.id} {pub2.title}")
            # when pub1 has no ID, then its not saved in database
            # so no need to save it my flagging it as duplicate
            if not pub1.id:
                continue
            # when the function is called with pub_model argument
            # return true when a duplicate if found
            if pub_model:
                return duplicate_mappings
    return duplicate_mappings


def review_duplicates(dry_run=True):
    # go through all the flagged duplicates that are pending a review
    duplicate_originals_map = flag_duplicates()
    for dpub_id in duplicate_originals_map:
        dpub = Publication.objects.get(id=dpub_id)
        opubs = [Publication.objects.get(id=oid) for oid in duplicate_originals_map[dpub_id]]
        for opub in opubs:
            print(f"Found duplicate publication: ")
            print("Publication 1: ", dpub.__repr__())
            print("Publication 2: ", opub.__repr__())
            print("Is publication ")
            is_duplicate = input("Is Publication 1 a duplicate? (y/n): ")
            with transaction.atomic():
                if is_duplicate == 'n':
                    dpub.status = Publication.STATUS_APPROVED
                elif is_duplicate != 'y':
                    dpub.reviewed = True
                    update_original_pub_source(opub, dpub)
                dpub.save()