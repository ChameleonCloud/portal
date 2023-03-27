# Functions to identify similarities in two publications to flag one of them as diplicate

import logging
from projects.user_publication.utils import PublicationUtils
from projects.models import Publication, PublicationSource
from django.db.models import Q
from django.db import transaction

logger = logging.getLogger(__name__)


def flag_duplicates(source, dry_run=True, pub_model=None):
    """
    flags duplicate publications in the database.
    When pub_model is supplied this model will be checked if it is a duplicate
    saves the model with status as DUPLICATE and if the pub_model is not already in database
    then the pub_model status is changed as DUPLICATE and lets downstream decide to save it or not

    Args:
        dry_run (bool, optional): If True, no changes will be made to the database. Defaults to True.
        pub_model (projects.models.Publication, optional): Publication model to check if it is a duplicate.
            Defaults to None, checks for all the publications if None
    Returns:
        (dict): keys are title of the publication that is flagged as duplicate
        values are ID of the original publication
    """
    # Exclude all publications with the status of 'rejected' or 'duplicate'
    exclude_status = Q(status=Publication.STATUS_REJECTED)
    exclude_status |= Q(status=Publication.STATUS_DUPLICATE)
    duplicate_mappings = {}

    # Get a list of publications to check for duplicates
    if pub_model:
        pubs_to_check_duplicates = [pub_model]
    else:
        # get the publications in reverse so latest can be checked against
        # old ones.
        pubs_to_check_duplicates = Publication.objects.exclude(exclude_status).order_by("-id")

    # Loop through each publication to check for duplicates
    for pub1 in pubs_to_check_duplicates:
        # Get a subset of publications with id less than the publication at question
        # and of same year as the publication at question to check against
        if not pub1.year:
            logger.info(f"{pub1.title} does not have year - ignoring")
            continue
        if not pub1.id:
            pubs_to_check_against = Publication.objects.filter(year=pub1.year).order_by('-id')
        else:
            pubs_to_check_against = Publication.objects.filter(id__lt=pub1.id, year=pub1.year).order_by('-id')
        pubs_to_check_against = pubs_to_check_against.exclude(exclude_status)

        # Loop through each subset publication to check against for duplicates
        for pub2 in pubs_to_check_against:
            # Check if pub1 and pub2 are similar enough to be flagged as duplicates
            if not PublicationUtils.is_pub_similar(pub1, pub2):
                continue
            pub1.status = Publication.STATUS_DUPLICATE
            pub1.is_reviewed = False
            duplicate_mappings[pub1.title] = pub2.id
            # Flag pub1 as a duplicate if it is not a dry run
            # add pub1's source as source to pub2 source
            if dry_run:
                # Log the publications that have been flagged as duplicates                
                logger.info(f"{pub1.title} is flagged duplicate to {pub2.id} {pub2.title}")
                continue
            # when pub1 has no ID, then its not saved in database
            # so no need to save it my flagging it as duplicate
            if not pub1.id:
                continue
            with transaction.atomic():
                pub1_sources = pub1.sources.all()
                for pub1_source in pub1_sources:
                    # copy all the objects's data to pub2_source
                    pub2_source = pub1_source
                    # assign pk as none so when save() a new object is created
                    pub2_source.pk = None
                    pub2_source.publication = pub2
                    pub2_source.is_found_by_algorithm = True
                    pub2_source.approved_with = PublicationSource.PENDING_REVIEW
                    pub2_source.save()
                pub1.save()
            # when the function is called with pub_model argument
            # return true when a dupplicate if found
            if pub_model:
                return duplicate_mappings
            # stop searching when pub1 is found as duplicate
            if pub1.status == Publication.STATUS_DUPLICATE:
                break
    return duplicate_mappings


def review_duplicates(dry_run=True):
    # go through all the flagged duplicates that are pending a review
    pass
