"""Registration emails wait in the outbox and are sent outside the request.

Approving or rejecting queues the email in the same transaction as the decision, so nobody is
approved without one. Sending happens in `manage.py send_outbox` (background mode), or right after
saving (inline mode, for local use and tests). Notices stop at the daily notice limit, which keeps a
reserve of the Brevo allowance for activation and password codes; codes are sent at once by
apps.accounts.mail and are only counted here.

States shown to the Admin: queued, waiting (queued beyond today's allowance), sent (accepted by
Brevo, not proof of delivery) and failed.
"""

import logging
import time
from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.accounts import mail
from apps.accounts.models import MailOutbox

logger = logging.getLogger('apps.accounts.outbox')

QUEUED = MailOutbox.Status.QUEUED
SENDING = MailOutbox.Status.SENDING
SENT = MailOutbox.Status.SENT
FAILED = MailOutbox.Status.FAILED
WAITING = 'waiting'
RETRY_MINUTES = (5, 15, 60, 60)  # waits after failed attempts 1 to 4; the fifth failure is final
MAX_ATTEMPTS = len(RETRY_MINUTES) + 1
STALE_CLAIM = timedelta(minutes=10)  # a send claimed longer ago than this died with its sender


def inline():
    return settings.MAIL_DELIVERY == 'inline'


def day_start():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def notice_limit():
    return max(0, settings.MAIL_DAILY_LIMIT - settings.MAIL_CODE_RESERVE)


def used_today():
    return MailOutbox.objects.filter(status=SENT, sent_at__gte=day_start()).count()


def notice_left():
    return max(0, notice_limit() - used_today())


DUPLICATE_NOTICE_GAP = timedelta(hours=6)


def _registration_rows():
    return MailOutbox.objects.filter(kind=MailOutbox.Kind.REGISTRATION)


def _queued_rows():
    """Everything the sender delivers: registration results and queued account notices."""
    return MailOutbox.objects.filter(kind__in=(MailOutbox.Kind.REGISTRATION, MailOutbox.Kind.NOTICE), status=QUEUED)


def queue_duplicate_registration_notice(user):
    """Queue the notice for an owner whose email or LRN was used in a new registration. Queued rather than sent,
    so the public answer takes the same time either way. At most one per DUPLICATE_NOTICE_GAP, so it cannot flood."""
    subject, body = mail.duplicate_registration_message(user)
    recent = MailOutbox.objects.filter(
        user=user, subject=subject, created_at__gte=timezone.now() - DUPLICATE_NOTICE_GAP
    ).exists()
    if recent or not user.email:
        return None
    row = MailOutbox.objects.create(kind=MailOutbox.Kind.NOTICE, to_email=user.email, subject=subject, body=body, user=user)
    return deliver_inline(row)


def queue_registration_result(registration, approved, reason=''):
    """Queue the approval or rejection email. Call inside the transaction that saves the decision."""
    subject, body = mail.registration_result_message(registration.user, approved, reason)
    return MailOutbox.objects.create(
        kind=MailOutbox.Kind.REGISTRATION,
        to_email=registration.user.email,
        subject=subject,
        body=body,
        registration=registration,
    )


def deliver(row, retry=True):
    """Send one row and record the outcome. Without retry a failure is final (inline mode)."""
    row.attempts += 1
    try:
        mail.send_message(row.to_email, row.subject, row.body)
    except mail.MailError as exc:
        row.last_error = str(exc)[:255]
        if retry and not exc.permanent and row.attempts < MAX_ATTEMPTS:
            row.status = QUEUED
            row.next_attempt_at = timezone.now() + timedelta(minutes=RETRY_MINUTES[row.attempts - 1])
        else:
            row.status = FAILED
    else:
        row.status = SENT
        row.sent_at = timezone.now()
        row.body = ''
        row.last_error = ''
    row.claimed_at = None
    row.save(update_fields=['status', 'attempts', 'last_error', 'next_attempt_at', 'claimed_at', 'sent_at', 'body'])
    return row


def deliver_inline(row):
    """In inline mode, send a freshly queued row now. In background mode the sender does it."""
    if inline():
        deliver(row, retry=False)
    return row


def _claim(row_id):
    claimed = MailOutbox.objects.filter(pk=row_id, status=QUEUED).update(status=SENDING, claimed_at=timezone.now())
    return claimed == 1


def release_stale():
    return MailOutbox.objects.filter(status=SENDING, claimed_at__lt=timezone.now() - STALE_CLAIM).update(
        status=QUEUED,
        claimed_at=None,
    )


def run_once(limit=100, seconds=180):
    """One sender round: due rows, oldest first, within the notice allowance and a time box."""
    release_stale()
    deadline = time.monotonic() + seconds
    result = {'sent': 0, 'retrying': 0, 'failed': 0}
    while sum(result.values()) < limit and time.monotonic() < deadline and notice_left() > 0:
        due = _queued_rows().filter(next_attempt_at__lte=timezone.now())
        row_id = due.order_by('id').values_list('id', flat=True).first()
        if row_id is None:
            break
        if not _claim(row_id):
            continue
        row = deliver(MailOutbox.objects.get(pk=row_id))
        result['sent' if row.status == SENT else 'retrying' if row.status == QUEUED else 'failed'] += 1
    result['waiting'] = summary()['waiting']
    return result


def resend_failed():
    """Queue every failed registration email again, with fresh attempts. Returns how many."""
    rows = _registration_rows().filter(status=FAILED)
    ids = list(rows.values_list('id', flat=True))
    rows.update(status=QUEUED, attempts=0, last_error='', next_attempt_at=timezone.now(), claimed_at=None)
    if inline():
        for row in MailOutbox.objects.filter(pk__in=ids):
            deliver(row, retry=False)
    return len(ids)


def prune():
    """Delete finished rows older than MAIL_KEEP_DAYS, so addresses are not kept for long.

    Activation rows of a live account stay: they are the Admin's count of codes sent to that person.
    """
    cutoff = timezone.now() - timedelta(days=settings.MAIL_KEEP_DAYS)
    old = MailOutbox.objects.filter(status__in=(SENT, FAILED), created_at__lt=cutoff)
    removed, _detail = old.exclude(kind=MailOutbox.Kind.ACTIVATION, user__isnull=False).delete()
    return removed


def _shown(row, allowed):
    if row.status == SENDING:
        return QUEUED
    if row.status == QUEUED:
        return QUEUED if row.id in allowed else WAITING
    return row.status


def _allowed_queued_ids():
    """Queued registration emails that fit today's remaining allowance, in sending order."""
    queued = _registration_rows().filter(status=QUEUED).order_by('id').values_list('id', flat=True)
    return set(queued[: notice_left()])


def state_of(row):
    """The shown state of one row: queued, waiting, sent or failed."""
    if row.status != QUEUED:
        return _shown(row, set())
    ahead = _registration_rows().filter(status=QUEUED, id__lt=row.id).count()
    return QUEUED if ahead < notice_left() else WAITING


def registration_states(registration_ids):
    """Latest email per registration, as {id: {'state', 'error'}}. Registrations with none are left out."""
    latest = {}
    for row in _registration_rows().filter(registration_id__in=registration_ids).order_by('registration_id', '-id'):
        latest.setdefault(row.registration_id, row)
    allowed = _allowed_queued_ids() if any(row.status == QUEUED for row in latest.values()) else set()
    return {
        registration_id: {'state': _shown(row, allowed), 'error': row.last_error if row.status == FAILED else ''}
        for registration_id, row in latest.items()
    }


def summary():
    """Counts for the Admin's delivery strip and the allowance warning before approving."""
    rows = _registration_rows()
    counts = dict(rows.order_by().values_list('status').annotate(total=Count('id')))
    left = notice_left()
    queued = counts.get(QUEUED, 0)
    waiting = max(0, queued - left)
    oldest = rows.filter(status__in=(QUEUED, SENDING)).order_by('created_at').values_list('created_at', flat=True).first()
    return {
        'delivery': settings.MAIL_DELIVERY,
        'queued': queued - waiting + counts.get(SENDING, 0),
        'waiting': waiting,
        'failed': counts.get(FAILED, 0),
        'sent_today': rows.filter(status=SENT, sent_at__gte=day_start()).count(),
        'used_today': used_today(),
        'notice_limit': notice_limit(),
        'notice_left': left,
        'oldest_queued_minutes': int((timezone.now() - oldest).total_seconds() // 60) if oldest else None,
    }
