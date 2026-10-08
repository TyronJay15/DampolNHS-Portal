"""Security events: written to the 'apps.security' log, and the serious ones to the audit log and the Admin.

Log lines name accounts by id, never by email, LRN or the text that was typed, and never include passwords,
tokens or codes.
"""

import logging

from rest_framework.throttling import BaseThrottle

from apps.accounts.identity import find_portal_user
from apps.accounts.models import User
from apps.accounts.throttles import record_failed_login
from apps.audit import services as audit

logger = logging.getLogger('apps.security')


def client_ip(request):
    """The visitor's address as DRF sees it (NUM_PROXIES decides which forwarded address is trusted)."""
    return BaseThrottle().get_ident(request)


def failed_sign_in(request, identifier):
    """Count a wrong password or unknown account; when an account reaches its limit, tell the Admin once."""
    user = find_portal_user(identifier)
    logger.warning('Failed sign-in for %s from %s', f'user {user.pk}' if user else 'an unknown account', client_ip(request))
    if record_failed_login(identifier) and user is not None:
        account_locked(user)


def account_locked(user):
    from apps.notifications.services import active_users, notify

    audit.record(
        user=user,
        action='login_locked',
        summary=f'Too many failed sign-ins for account #{user.pk}; sign-in paused for that account',
        target_type='User',
        target_id=user.pk,
    )
    notify(
        active_users(User.Role.ADMIN),
        'Sign-in paused after failed attempts',
        f'Account #{user.pk} ({user.get_role_display()}) had too many wrong passwords. Sign-in for it is paused for up '
        'to an hour. If the person did not do this, their password may be targeted: ask them to change it.',
        level='warning',
        category='security',
    )
    logger.warning('Sign-in paused for user %s after repeated failures', user.pk)
