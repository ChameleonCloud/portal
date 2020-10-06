import os
import sys
import logging
import django

# loading up django so we can use models for queries/updates
sys.path.append('/project')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chameleon.settings")
django.setup()
logger = logging.getLogger('util.scripts.sync_tas.sync_pi_status')

from django.conf import settings
from django.contrib.auth import get_user_model
from pytas.http import TASClient
from chameleon.models import PIEligibility
from django.utils import timezone
from datetime import datetime
import argparse

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(\
        description='Import PI eligibility status from TAS')
    parser.add_argument('--dryrun', action='store_true', default=False, help=\
        'Simulate import, no changes applied')
    parser.add_argument('--users', type=str, help=\
        'Synchronize a specific user or set of users using a csv list of usernames', default=None)
    parser.add_argument('--seteligible', action='store_true', default=False, help=\
        'Used with --users flag to set all provided users as PI Eligible')
    args = parser.parse_args(argv[1:])

    started = datetime.now()
    logger.info('Starting... {0}'.format(started))
    usermodel = get_user_model()
    if args.users:
        usernames = args.users.split(',')
        users = usermodel.objects.filter(username__in=usernames)
    else:
        users = usermodel.objects.all()

    if args.users and args.seteligible:
        updated = set_all_pi_status(args.dryrun, users, "Eligible")
    else:
        updated = import_pi_status(args.dryrun, users, TASClient())

    finished = datetime.now()
    if(args.dryrun):
        logger.info('Dry run, no updates made')

    logger.info('############ Finished ############')
    for i in updated:
        logger.info(i)
    logger.info('{0} users updated'.format(str(len(updated))))
    logger.info('############ Finished ############')
    logger.info('Started... {0}'.format(started))
    logger.info('Finished... {0}'.format(finished))
    delta = finished - started
    logger.info('elapsed seconds = {0}'.format(delta.total_seconds()))

def import_pi_status(dryrun=False, users=[], tas=None):
    updated = []

    for index, user in enumerate(users):
        percent_complete = int(index/float(users.count()) * 100)
        logger.info('{0} of {1}, {2}% complete, next: {3}'.format(\
            index, users.count(), percent_complete, user.username))
        if user.pi_eligibility().lower() == 'ineligible':
            ''' user is ineligible in portal, let's see if TAS says different '''
            tas_pi_status = get_tas_pi_status(tas, user.username)
            if tas_pi_status.lower() != user.pi_eligibility().lower():
                ''' TAS PI Status doesn't match portal, let's update '''
                save_pi_status(user, tas_pi_status, dryrun)
                updated.append((user.username, tas_pi_status))
            else:
                logger.debug('{0} already synced: {1}'.format(user.username, tas_pi_status))
        else:
            logger.debug('Skipping {0} portal pi eligibility is: {1}'.format(\
                user.username, user.pi_eligibility()))
    return updated

def set_all_pi_status(dryrun=False, users=[], status=None):
    updated = []
    for index, user in enumerate(users):
        percent_complete = int(index/float(users.count()) * 100)
        logger.info('{0} of {1}, {2}% complete, next: {3}'.format(\
            index, users.count(), percent_complete, user.username))
        if user.pi_eligibility().lower() == status.lower():
            logger.info('pi_eligibility {0} already set for user {1}'.format(\
                status, user.username))
            continue
        save_pi_status(user, status, dryrun)
        updated.append((user.username, status))
    return updated

def get_tas_pi_status(tas, username):
    try:
        return tas.get_user(username=username)['piEligibility']
    except:
        logger.error('Error getting pi status for user: {0}'.format(username), sys.exc_info()[0])
        return 'Ineligible'

def save_pi_status(user, status, dryrun=False):
    pie = PIEligibility()
    pie.requestor = user
    pie.status = status.upper()
    pie.review_summary = 'Imported From TAS'
    pie.review_date = timezone.now()
    if(dryrun):
        logger.info('Dry run, TAS PI Status {0} for user {1} not updated'.format(\
            status, user.username))
        return
    else:
        logger.info('User {0} updated, PI Status: {1}'.format(user.username, status))
        pie.save()

if __name__=="__main__":
    main()
