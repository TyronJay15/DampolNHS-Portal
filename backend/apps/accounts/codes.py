import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.accounts.models import EmailCode


def print_portal_code(user, purpose, code):
    if not getattr(settings, 'MAIL_PRINT_CODES', False):
        return
    label = 'ACTIVATION' if purpose == 'activate' else 'PASSWORD'
    print('', flush=True)
    print(f'=== {label} CODE ===', flush=True)
    print(user.email, flush=True)
    print(code, flush=True)
    print('====================', flush=True)


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


def consume_code(user, purpose, raw):
    row = (
        EmailCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by('-created_at')
        .first()
    )
    if row is None or row.expires_at < timezone.now() or not check_password(str(raw or ''), row.code_hash):
        return False
    row.used_at = timezone.now()
    row.save(update_fields=['used_at'])
    return True
