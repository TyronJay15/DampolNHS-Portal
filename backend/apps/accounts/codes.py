import math
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import EmailCode

RESEND_SECONDS = 60
MAX_ATTEMPTS = 5


def print_portal_code(user, purpose, code):
    """Dev only (MAIL_PRINT_CODES): show the code in the server terminal and keep the latest in a log file.

    The file covers a server started without a visible terminal. It is git-ignored (*.log).
    """
    if not getattr(settings, 'MAIL_PRINT_CODES', False):
        return
    label = 'ACTIVATION' if purpose == 'activate' else 'PASSWORD'
    print('', flush=True)
    print(f'=== {label} CODE ===', flush=True)
    print(user.email, flush=True)
    print(code, flush=True)
    print('====================', flush=True)
    try:
        with open(settings.BASE_DIR / 'dev_codes.log', 'a', encoding='utf-8') as handle:
            handle.write(f'{timezone.now():%Y-%m-%d %H:%M:%S}  {label}  {user.email}  {code}\n')
    except OSError:
        pass


def issue_code(user, purpose, minutes=24 * 60):
    EmailCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).delete()
    raw = f'{secrets.randbelow(1_000_000):06d}'
    EmailCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(raw),
        expires_at=timezone.now() + timedelta(minutes=minutes),
    )
    print_portal_code(user, purpose, raw)
    return raw


def _live_code(user, purpose):
    return (
        EmailCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by('-created_at')
        .first()
    )


def resend_wait(user, purpose):
    """Seconds before another code may be sent; 0 when one can go out now."""
    row = _live_code(user, purpose)
    if row is None:
        return 0
    elapsed = (timezone.now() - row.created_at).total_seconds()
    return max(0, math.ceil(RESEND_SECONDS - elapsed))


def _matching_code(user, purpose, raw):
    """The live code when raw matches it. Each wrong guess counts; MAX_ATTEMPTS of them cancel the code."""
    row = _live_code(user, purpose)
    if row is None or row.expires_at < timezone.now():
        return None
    if check_password(str(raw or ''), row.code_hash):
        return row
    row.attempts += 1
    if row.attempts >= MAX_ATTEMPTS:
        row.expires_at = timezone.now()
    row.save(update_fields=['attempts', 'expires_at'])
    return None


def check_code(user, purpose, raw):
    return _matching_code(user, purpose, raw) is not None


def consume_code(user, purpose, raw):
    row = _matching_code(user, purpose, raw)
    if row is None:
        return False
    row.used_at = timezone.now()
    row.save(update_fields=['used_at'])
    return True
