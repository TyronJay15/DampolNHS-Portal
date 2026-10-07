"""Sign-in sessions: the only place refresh tokens are issued, rotated, checked and ended.

A sign-in creates one AuthSession. The browser holds its refresh token in an HttpOnly cookie (never readable by
JavaScript) and the short-lived access token in memory. Each refresh uses the token once and issues the next one,
so a copied token stops working as soon as the real browser refreshes. If a used token comes back after the grace
window, the whole session is ended (replay detection), audited and reported to the administrators.

Limits (settings): AUTH_ACCESS_MINUTES (access token), AUTH_IDLE_MINUTES (no refresh for this long ends the
session), AUTH_SESSION_HOURS (hard limit from sign-in), AUTH_REFRESH_GRACE_SECONDS (a just-used token presented
again inside this window is a race between two requests, answered with a conflict, not treated as theft).
"""

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import AuthSession, SessionToken, User
from apps.audit import services as audit

logger = logging.getLogger(__name__)


class SessionInvalid(Exception):
    """The refresh token is unknown, used, expired or belongs to an ended session. The user must sign in."""


class SessionConflict(Exception):
    """The token was used a moment ago by another request from the same browser. Retry with the new cookie."""


def _hash(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _new_token(session):
    raw = secrets.token_urlsafe(32)
    SessionToken.objects.create(session=session, token_hash=_hash(raw))
    return raw


def start(user):
    """Open a session for a user who passed every sign-in step. Returns (session, refresh token)."""
    now = timezone.now()
    with transaction.atomic():
        session = AuthSession.objects.create(
            user=user,
            last_refreshed_at=now,
            expires_at=now + timedelta(hours=settings.AUTH_SESSION_HOURS),
        )
        return session, _new_token(session)


def access_token(session):
    """A short-lived access token tied to the session. It never outlives the session's hard limit."""
    token = AccessToken.for_user(session.user)
    token['sid'] = str(session.pk)
    lifetime = timedelta(minutes=settings.AUTH_ACCESS_MINUTES)
    remaining = session.expires_at - timezone.now()
    token.set_exp(lifetime=min(lifetime, max(remaining, timedelta(seconds=1))))
    return str(token)


def rotate(raw):
    """Use a refresh token once. Returns (session, next refresh token) or raises SessionInvalid / SessionConflict."""
    if not raw or len(raw) > 200:
        raise SessionInvalid()
    now = timezone.now()
    # The session's end is saved before raising: an exception inside the transaction would undo it.
    with transaction.atomic():
        token = (
            SessionToken.objects.select_for_update()
            .select_related('session__user')
            .filter(token_hash=_hash(raw))
            .first()
        )
        if token is None or token.session.ended_at is not None:
            raise SessionInvalid()
        session = token.session
        if token.used_at is not None:
            if now - token.used_at <= timedelta(seconds=settings.AUTH_REFRESH_GRACE_SECONDS):
                raise SessionConflict()
            reason = AuthSession.EndReason.REPLAY
        elif session.expires_at <= now:
            reason = AuthSession.EndReason.EXPIRED
        elif now - session.last_refreshed_at > timedelta(minutes=settings.AUTH_IDLE_MINUTES):
            reason = AuthSession.EndReason.IDLE
        elif not session.user.can_sign_in:
            reason = AuthSession.EndReason.ACCOUNT
        else:
            token.used_at = now
            token.save(update_fields=['used_at'])
            session.last_refreshed_at = now
            session.save(update_fields=['last_refreshed_at'])
            return session, _new_token(session)
        _end(session, reason, now)
    if reason == AuthSession.EndReason.REPLAY:
        _report_replay(session)
    raise SessionInvalid()


def end(session, reason):
    """End one session (sign-out). Ending an ended session changes nothing."""
    with transaction.atomic():
        locked = AuthSession.objects.select_for_update().filter(pk=session.pk, ended_at__isnull=True).first()
        if locked is not None:
            _end(locked, reason, timezone.now())


def end_by_token(raw, reason):
    """Sign-out with only the refresh cookie at hand. Unknown or already-ended tokens are ignored."""
    if not raw or len(raw) > 200:
        return None
    token = SessionToken.objects.select_related('session').filter(token_hash=_hash(raw)).first()
    if token is None:
        return None
    end(token.session, reason)
    return token.session


def end_all(user, reason, keep=None):
    """End every open session of a user, for example after a password reset or when the account closes."""
    now = timezone.now()
    open_sessions = AuthSession.objects.filter(user=user, ended_at__isnull=True)
    if keep is not None:
        open_sessions = open_sessions.exclude(pk=keep.pk)
    return open_sessions.update(ended_at=now, end_reason=reason)


def session_for_access(validated_token, user):
    """The open session an access token belongs to, or None. Used on every authenticated request."""
    sid = validated_token.get('sid')
    if not sid:
        return None
    return AuthSession.objects.filter(
        pk=sid, user=user, ended_at__isnull=True, expires_at__gt=timezone.now()
    ).first()


def purge(older_than_days=30):
    """Delete sessions that ended or expired long ago, with their token hashes. Run daily by `cleanup_sessions`."""
    cutoff = timezone.now() - timedelta(days=older_than_days)
    stale = AuthSession.objects.filter(expires_at__lt=cutoff) | AuthSession.objects.filter(ended_at__lt=cutoff)
    count, _ = stale.delete()
    return count


def _end(session, reason, now):
    session.ended_at = now
    session.end_reason = reason
    session.save(update_fields=['ended_at', 'end_reason'])


def _report_replay(session):
    """A used refresh token came back: the session is already ended. Record it and tell the administrators."""
    from apps.notifications.services import active_users, notify

    user = session.user
    audit.record(
        user=user,
        action='session_replay_detected',
        summary='A used sign-in token was presented again; that sign-in was ended',
        target_type='User',
        target_id=user.pk,
        details={'session': str(session.pk)},
    )
    notify(
        active_users(User.Role.ADMIN),
        'Possible stolen sign-in',
        f'An old sign-in token for user #{user.pk} ({user.get_role_display()}) was used again, so that sign-in was '
        'ended. Ask the person to change their password if this repeats.',
        level='warning',
        category='security',
    )
    logger.warning('Refresh token replay detected for user %s; session %s ended.', user.pk, session.pk)
