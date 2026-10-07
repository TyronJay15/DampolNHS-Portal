"""Who may use the Django admin console (security plan W7). Run on the server only.

  --maintenance EMAIL     full console access (superuser), for the people who maintain the system
  --content-editor EMAIL  console access limited to the chatbot FAQs, for the portal Admin
  --revoke EMAIL          no console access

Every console sign-in also needs the account's authenticator code, so the person must set up the app in the portal
first. Each change is audited.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.console import content_editors_group
from apps.accounts.models import User
from apps.audit import services as audit


class Command(BaseCommand):
    help = 'Grant or remove access to the Django admin console.'

    def add_arguments(self, parser):
        choice = parser.add_mutually_exclusive_group(required=True)
        choice.add_argument('--maintenance', metavar='EMAIL')
        choice.add_argument('--content-editor', metavar='EMAIL')
        choice.add_argument('--revoke', metavar='EMAIL')

    def handle(self, *args, **options):
        email = options['maintenance'] or options['content_editor'] or options['revoke']
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError('No account has that email.')
        group = content_editors_group()
        if options['maintenance']:
            user.is_staff, user.is_superuser, level = True, True, 'maintenance'
            user.groups.remove(group)
        elif options['content_editor']:
            user.is_staff, user.is_superuser, level = True, False, 'content editor'
            user.groups.add(group)
        else:
            user.is_staff, user.is_superuser, level = False, False, 'none'
            user.groups.remove(group)
        user.save(update_fields=['is_staff', 'is_superuser'])
        audit.record(
            user=None,
            action='console_access_changed',
            summary=f'Console access of account #{user.pk} set to {level}',
            target_type='User',
            target_id=user.pk,
            details={'level': level, 'by': 'server command'},
        )
        self.stdout.write(self.style.SUCCESS(f'Console access of account #{user.pk} is now: {level}.'))
