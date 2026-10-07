"""Break-glass: remove an account's authenticator app from the server command line.

For when every administrator has lost their phone and recovery codes, so nobody can use the portal's reset. Only
people with access to the server can run it. The account's sign-ins are ended, the reset is audited, and the
person must set up the app again at their next sign-in.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import mfa, sessions
from apps.accounts.models import AuthSession, User
from apps.audit import services as audit


class Command(BaseCommand):
    help = 'Remove the authenticator app of one account (break-glass). The person sets it up again at next sign-in.'

    def add_arguments(self, parser):
        parser.add_argument('email', help='Email of the account to reset.')

    def handle(self, *args, **options):
        user = User.objects.filter(email__iexact=options['email'].strip()).first()
        if user is None:
            raise CommandError('No account has that email.')
        mfa.remove(user)
        ended = sessions.end_all(user, AuthSession.EndReason.ADMIN)
        audit.record(
            user=None,
            action='mfa_reset',
            summary=f'Server command reset the authenticator app of account #{user.pk}',
            target_type='User',
            target_id=user.pk,
            details={'sign_ins_ended': ended, 'by': 'server command'},
        )
        self.stdout.write(self.style.SUCCESS(f'Authenticator removed for account #{user.pk}; {ended} sign-in(s) ended.'))
