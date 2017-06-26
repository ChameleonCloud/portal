from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from pytas.http import TASClient

class Command(BaseCommand):
    help = 'Sync local user emails with TAS information'

    def handle(self, *args, **options):
        users = User.objects.all()
        tas = TASClient()

        print(self.style)
        for u in users:
            tas_user = tas.get_user(username=u.username)
            if u.email != tas_user['email']:
                self.stdout.write(self.style.ERROR('MISMATCH! %s is %s in TAS! Updating.' % (u.email, tas_user['email'])))
                # TODO figure out how to log this? It's probably logged to journalctl on stdout!
                u.email = tas_user['email']
                u.save()

            #else:
                #self.stdout.write(self.style.NOTICE('User %s has a matching email in TAS' % u.username))

