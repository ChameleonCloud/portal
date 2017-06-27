from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from optparse import make_option
from pytas.http import TASClient

class Command(BaseCommand):
    help = 'Sync local user emails with TAS information. ' \
           'Takes username as an optional argument. If no username is provided, will loop through all users ' \
           'and check their local email against their TAS email. Use the --skip-confirm flag to skip confirmation (example, if run as a cron job)'

    option_list = BaseCommand.option_list + (
        make_option('--username',
                            dest='username',
                            help='Specify a user to check and update'),
        make_option('--skip-confirm',
                            action='store_true',
                            dest='skip_confirm',
                            default=False,
                            help='Don\'t ask for confirmation to update user emails')
    )

    ## This is the way the current version of django does it, we're using a much older version
    #def add_arguments(self, parser):
    #    parser.add_argument('--usernames',
    #                        dest='usernames',
    #                        nargs='*',
    #                        help='A list of users to check and update',
    #                        default=parser.SUPPRESS)
    #    parser.add_argument('--skip-confirm',
    #                        action='store_true',
    #                        dest='skip_confirm',
    #                        default=False,
    #                        help='Don\'t ask for confirmation to update user emails')

    def handle(self, *args, **options):
        users = []
        tas = TASClient()

        if options['username']:
            u = options['username']
            try:
                djangoUser = User.objects.get(username=u)
                users.append(djangoUser)
            except ObjectDoesNotExist:
                self.stdout.write(self.style.ERROR('No user with username %s' % u))

        else:
            users = User.objects.all()


        usersToUpdate = []
        for u in users:
            tas_user = tas.get_user(username=u.username)
            if u.email != tas_user['email']:
                self.stdout.write(self.style.ERROR('For User %s: %s (Chameleon), %s (TAS)' % (u.username, u.email, tas_user['email'])))
                u.email = tas_user['email']
                usersToUpdate.append(u)


        if len(usersToUpdate) > 0:
            if options['skip_confirm']:
                self._run_update(usersToUpdate)
            else:
                self.stdout.write(self.style.NOTICE('%s users will have their emails synced with TAS. Continue?' % len(usersToUpdate)))
                confirm = raw_input('Y/N: ')

                if confirm == 'Y' or confirm == 'y':
                    self.stdout.write(self.style.NOTICE('Updating user emails'))
                    self._run_update(usersToUpdate)

                else:
                    self.stdout.write(self.style.NOTICE('Cancelling user email sync'))
        else:
            self.stdout.write(self.style.NOTICE('There are no user emails to update'))


    def _run_update(self, usersToUpdate):
        for u in usersToUpdate:
            #self.stdout.write(self.style.NOTICE('If I were actually running I\'d be updating %s ' % u.username))
            u.save()
