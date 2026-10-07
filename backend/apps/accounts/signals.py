"""Only the Django admin console signs in with a Django session, so every user_logged_in is a console sign-in.
Each one is audited and reported to the administrators (security plan W7)."""

import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.accounts.models import User
from apps.audit import services as audit

logger = logging.getLogger('apps.security')


@receiver(user_logged_in)
def console_sign_in(sender, request, user, **kwargs):
    from apps.notifications.services import active_users, notify

    audit.record(
        user=user,
        action='django_admin_login',
        summary=f'Account #{user.pk} signed in to the maintenance console',
        target_type='User',
        target_id=user.pk,
    )
    notify(
        active_users(User.Role.ADMIN),
        'Maintenance console sign-in',
        f'Account #{user.pk} signed in to the Django maintenance console. If nobody planned maintenance now, change '
        'the console path and that account\'s password.',
        level='warning',
        category='security',
    )
    logger.warning('Maintenance console sign-in by user %s', user.pk)
