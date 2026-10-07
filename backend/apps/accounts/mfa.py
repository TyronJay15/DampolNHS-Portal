"""The authenticator-app step for Admin and Head Teacher sign-ins (security plan W3).

Built on django-otp: its TOTP implementation checks the 6-digit codes (30-second steps, one step of clock
tolerance) and its throttling doubles the wait after each wrong code. A code can be used once: the step of the last
accepted code is stored, and only later steps are accepted. The shared secret is encrypted with
MFA_ENCRYPTION_KEY (Fernet). Recovery codes are random, shown once, stored as keyed hashes, and each works once.

Sign-in with the second step: the password step returns a challenge (a signed, five-minute token naming the user
and the purpose). No session, access token or refresh cookie exists until the code is accepted.
"""

import base64
import hashlib
import hmac
import io
import secrets
import time
from base64 import b32encode

import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django_otp.oath import TOTP

from apps.accounts.models import AuthenticatorDevice, RecoveryCode, User

ISSUER = 'Dampol 1st NHS Portal'
RECOVERY_CODE_COUNT = 10
CHALLENGE_SECONDS = 300
_CHALLENGE_SALT = 'apps.accounts.mfa.challenge'
VERIFY = 'verify'
ENROLL = 'enroll'


class ChallengeInvalid(Exception):
    """The challenge expired, was altered, or no longer matches the account."""


# ---- Who needs it ----

def required_for(user):
    """Admin and Head Teacher accounts must use the second step once enforcement is on (MFA_ENFORCED)."""
    return settings.MFA_ENFORCED and user.role in (User.Role.ADMIN, User.Role.HEAD_TEACHER)


def device_for(user, confirmed=True):
    return AuthenticatorDevice.objects.filter(user=user, confirmed=confirmed).first()


def sign_in_step(user):
    """After a correct password: None (no second step), VERIFY (enter a code) or ENROLL (set up the app first)."""
    if device_for(user) is not None:
        return VERIFY
    if required_for(user):
        return ENROLL
    return None


# ---- Challenges between the password step and the code step ----

def _password_marker(user):
    # Part of the password hash: a password change in between makes the challenge worthless.
    return hashlib.sha256(user.password.encode()).hexdigest()[:16]


def issue_challenge(user, purpose):
    return signing.dumps({'uid': user.pk, 'purpose': purpose, 'pw': _password_marker(user)}, salt=_CHALLENGE_SALT)


def read_challenge(value, purpose):
    try:
        data = signing.loads(str(value or ''), salt=_CHALLENGE_SALT, max_age=CHALLENGE_SECONDS)
    except signing.BadSignature as exc:
        raise ChallengeInvalid() from exc
    user = User.objects.filter(pk=data.get('uid')).first()
    if user is None or data.get('purpose') != purpose or data.get('pw') != _password_marker(user) or not user.can_sign_in:
        raise ChallengeInvalid()
    return user


# ---- Secrets ----

def _fernet():
    key = settings.MFA_ENCRYPTION_KEY
    if not key:
        # Development and tests only; production refuses to start without MFA_ENCRYPTION_KEY.
        key = base64.urlsafe_b64encode(hashlib.sha256(f'mfa:{settings.SECRET_KEY}'.encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(raw):
    return _fernet().encrypt(raw).decode()


def _decrypt(device):
    try:
        return _fernet().decrypt(device.secret.encode())
    except InvalidToken as exc:
        raise RuntimeError('The authenticator secret cannot be read with the current MFA_ENCRYPTION_KEY.') from exc


# ---- Enrollment ----

def start_enrollment(user):
    """A new, unconfirmed device. Returns (secret for typing in, otpauth address, QR code as SVG text)."""
    raw = secrets.token_bytes(20)
    with transaction.atomic():
        AuthenticatorDevice.objects.filter(user=user, confirmed=False).delete()
        AuthenticatorDevice.objects.create(user=user, name='Authenticator app', confirmed=False, secret=_encrypt(raw))
    secret = b32encode(raw).decode()
    uri = f'otpauth://totp/{_label(user)}?secret={secret}&issuer={_quoted(ISSUER)}&algorithm=SHA1&digits=6&period=30'
    return secret, uri, _qr_svg(uri)


def confirm_enrollment(user, code):
    """Accept the first code from the app. Replaces any older device. Returns the new recovery codes or None."""
    with transaction.atomic():
        device = AuthenticatorDevice.objects.select_for_update().filter(user=user, confirmed=False).first()
        if device is None or not verify_totp(device, code):
            return None
        AuthenticatorDevice.objects.filter(user=user, confirmed=True).delete()
        device.confirmed = True
        device.save(update_fields=['confirmed'])
        return new_recovery_codes(user)


def remove(user):
    """Turn the second step off for this user: the device and every recovery code go."""
    with transaction.atomic():
        AuthenticatorDevice.objects.filter(user=user).delete()
        RecoveryCode.objects.filter(user=user).delete()


# ---- Checking codes ----

def verify_totp(device, token):
    """django-otp's TOTP check with replay protection and the wrong-code back-off. Call inside a transaction."""
    allowed, _ = device.verify_is_allowed()
    if not allowed:
        return False
    text = str(token or '').strip().replace(' ', '')
    verified = False
    if text.isdigit() and len(text) == 6:
        totp = TOTP(_decrypt(device), step=30, t0=0, digits=6, drift=device.drift)
        totp.time = time.time()
        verified = totp.verify(int(text), tolerance=1, min_t=device.last_t + 1)
        if verified:
            device.last_t = totp.t()
            device.drift = totp.drift
            device.throttle_reset(commit=False)
            device.set_last_used_timestamp(commit=False)
            device.save()
    if not verified:
        device.throttle_increment(commit=True)
    return verified


def verify_code(user, code):
    """Check a sign-in code: an authenticator code, or else an unused recovery code. Returns 'totp', 'recovery'
    or None."""
    with transaction.atomic():
        device = AuthenticatorDevice.objects.select_for_update().filter(user=user, confirmed=True).first()
        if device is None:
            return None
        allowed, _ = device.verify_is_allowed()
        if not allowed:
            return None
        if verify_totp(device, code):
            return 'totp'
        if use_recovery_code(user, code):
            device.throttle_reset(commit=True)
            return 'recovery'
    return None


def wait_seconds(user):
    """Seconds until another code may be tried after repeated wrong codes; 0 when trying is allowed."""
    device = device_for(user)
    if device is None:
        return 0
    allowed, data = device.verify_is_allowed()
    if allowed or not data or not data.get('locked_until'):
        return 0
    return max(1, int((data['locked_until'] - timezone.now()).total_seconds()))


# ---- Recovery codes ----

def _code_hash(code):
    normalized = str(code or '').strip().replace('-', '').replace(' ', '').upper()
    key = (settings.MFA_ENCRYPTION_KEY or settings.SECRET_KEY).encode()
    return hmac.new(key, normalized.encode(), hashlib.sha256).hexdigest()


def new_recovery_codes(user):
    """Replace the user's recovery codes with RECOVERY_CODE_COUNT new ones. Returns them; they are never shown again."""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O or 1/I to misread
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = ''.join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f'{raw[:5]}-{raw[5:]}')
    with transaction.atomic():
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create([RecoveryCode(user=user, code_hash=_code_hash(code)) for code in codes])
    return codes


def use_recovery_code(user, code):
    text = str(code or '').strip()
    if len(text.replace('-', '').replace(' ', '')) != 10:
        return False
    used = RecoveryCode.objects.filter(user=user, code_hash=_code_hash(text), used_at__isnull=True).update(
        used_at=timezone.now()
    )
    return used == 1


def recovery_codes_left(user):
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


# ---- Helpers ----

def _quoted(text):
    from urllib.parse import quote

    return quote(text, safe='')


def _label(user):
    return f'{_quoted(ISSUER)}:{_quoted(user.email)}'


def _qr_svg(uri):
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode()
