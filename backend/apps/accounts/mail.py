import json
import logging
from html import escape
from smtplib import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPDataError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.accounts.models import MailOutbox

logger = logging.getLogger('apps.accounts.mail')
FALLBACK_PORT = 2525  # Brevo's alternative when the usual port is blocked
BREVO_URL = 'https://api.brevo.com/v3/smtp/email'


class MailError(RuntimeError):
    """A send that did not go through. permanent: retrying the same message cannot help."""

    def __init__(self, message, permanent=False):
        super().__init__(message)
        self.permanent = permanent


def _from_header():
    name = getattr(settings, 'EMAIL_FROM_NAME', 'Dampol 1st NHS')
    address = settings.DEFAULT_FROM_EMAIL
    return f'{name} <{address}>'


def _html_body(subject, body):
    blocks = []
    for line in body.split('\n'):
        if line.strip():
            blocks.append(f'<p style="margin:0 0 12px;line-height:1.55">{escape(line)}</p>')
        else:
            blocks.append('<p style="margin:0 0 12px">&nbsp;</p>')
    return (
        '<!DOCTYPE html><html><body style="margin:0;background:#eef4ef;padding:24px;'
        'font-family:Georgia,serif;color:#163523">'
        '<div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:16px;'
        'padding:24px 28px;border:1px solid #d5e0d7">'
        '<p style="margin:0 0 8px;color:#c4a035;letter-spacing:.08em;text-transform:uppercase;'
        'font-size:12px;font-weight:700">Dampol 1st NHS</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px;color:#163523">{escape(subject)}</h1>'
        f'{"".join(blocks)}'
        '</div></body></html>'
    )


def _smtp_ready():
    backend = settings.EMAIL_BACKEND
    if 'console' in backend:
        raise MailError('Mail is using the console backend. Restart Django so SMTP is loaded.')
    if 'smtp' in backend and not (settings.EMAIL_HOST_PASSWORD or '').strip():
        raise MailError('EMAIL_HOST_PASSWORD is missing from backend/.env.')
    return backend


def _message(to, subject, body, port):
    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=port,
        username=settings.EMAIL_HOST_USER,
        password=(settings.EMAIL_HOST_PASSWORD or '').strip(),
        use_tls=True,
        use_ssl=False,
        timeout=settings.EMAIL_TIMEOUT,
        fail_silently=False,
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=_from_header(),
        to=[to],
        reply_to=[settings.DEFAULT_FROM_EMAIL],
        connection=connection,
    )
    message.attach_alternative(_html_body(subject, body), 'text/html')
    message.extra_headers['X-Auto-Response-Suppress'] = 'All'
    return message


def send_message(to, subject, body):
    """Send one email with the configured transport. Raises MailError and writes nothing to the database."""
    if settings.MAIL_TRANSPORT == 'brevo_api':
        return _send_brevo(to, subject, body)
    return _send_smtp(to, subject, body)


def masked(address):
    """An address for the server log: enough to tell messages apart, not enough to read who they went to."""
    name, _, domain = str(address or '').partition('@')
    return f'{name[:1]}***@{domain}' if domain else '***'


def _send_brevo(to, subject, body):
    """Brevo's HTTPS API, for hosts that block SMTP. The API key stays on the server, in a header."""
    payload = json.dumps(
        {
            'sender': {'name': settings.EMAIL_FROM_NAME, 'email': settings.DEFAULT_FROM_EMAIL},
            'to': [{'email': to}],
            'replyTo': {'email': settings.DEFAULT_FROM_EMAIL},
            'subject': subject,
            'textContent': body,
            'htmlContent': _html_body(subject, body),
            'headers': {'X-Auto-Response-Suppress': 'All'},
        }
    ).encode()
    request = Request(
        BREVO_URL,
        data=payload,
        method='POST',
        headers={'accept': 'application/json', 'content-type': 'application/json', 'api-key': settings.BREVO_API_KEY},
    )
    try:
        with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
            response.read()
    except HTTPError as exc:
        # 400 means the message or address is wrong, so a retry cannot help. Key problems (401/403) and
        # limits or outages (429, 5xx) are worth retrying once fixed or later.
        raise MailError(f'Brevo refused the email for {to} ({exc.code}).', permanent=exc.code == 400) from exc
    except (URLError, OSError) as exc:
        raise MailError(f'Could not reach Brevo. {getattr(exc, "reason", exc)}') from exc
    logger.info('Mail accepted for %s via the Brevo API', masked(to))
    return 1


def _send_smtp(to, subject, body):
    """One SMTP connection, trying the fallback port if the usual one is unreachable.

    smtplib errors are OSErrors too, so the specific ones are caught first.
    """
    backend = _smtp_ready()
    ports = [settings.EMAIL_PORT]
    if 'smtp' in backend and settings.EMAIL_PORT != FALLBACK_PORT:
        ports.append(FALLBACK_PORT)
    unreachable = None
    for port in ports:
        try:
            sent = _message(to, subject, body, port).send(fail_silently=False)
        except SMTPAuthenticationError as exc:
            raise MailError(f'SMTP login was rejected ({exc.smtp_code}). Check the Brevo SMTP key.') from exc
        except SMTPRecipientsRefused as exc:
            raise MailError(f'The mail server refused {to}.', permanent=True) from exc
        except SMTPDataError as exc:
            raise MailError(f'Mail was rejected for {to} ({exc.smtp_code}).', permanent=exc.smtp_code >= 500) from exc
        except (SMTPConnectError, SMTPServerDisconnected) as exc:
            unreachable = exc
        except SMTPException as exc:
            raise MailError(f'Mail was rejected for {to}. {getattr(exc, "smtp_code", "")}'.strip()) from exc
        except OSError as exc:
            unreachable = exc
        else:
            if not sent:
                raise MailError(f'Mail was not accepted for {to}.')
            logger.info('Mail accepted for %s via %s:%s', masked(to), backend, port)
            return sent
    raise MailError(f'Could not reach the mail server. {unreachable}') from unreachable


def _log(to, subject, kind, user, **fields):
    """Record mail sent at once. Its body is never stored, so a code cannot leak from the log."""
    try:
        with transaction.atomic():
            MailOutbox.objects.create(kind=kind, to_email=to, subject=subject[:200], user=user, attempts=1, **fields)
    except DatabaseError:
        logger.exception('Could not log the mail for %s', masked(to))


def send_portal_mail(to, subject, body, kind=MailOutbox.Kind.NOTICE, user=None):
    """Send now, for codes and account notices, and log it. Raises MailError."""
    sent = send_message(to, subject, body)
    _log(to, subject, kind, user, status=MailOutbox.Status.SENT, sent_at=timezone.now())
    return sent


def _try_send(to, subject, body, kind, user):
    """Send a code without breaking the request. A failure is logged for the Admin. Returns whether it went out."""
    try:
        send_portal_mail(to, subject, body, kind, user)
    except MailError as exc:
        # No traceback: the error text names the address. The full reason is kept in the outbox row for the Admin.
        logger.warning('Mail to %s was not sent (%s).', masked(to), 'permanent' if exc.permanent else 'retryable')
        _log(to, subject, kind, user, status=MailOutbox.Status.FAILED, last_error=str(exc)[:255])
        return False
    return True


def activation_email(user, code):
    """Email the activation code. Returns whether it went out."""
    return _try_send(
        user.email,
        'Dampol 1st NHS activation code',
        (
            f'Hello {user.first_name},\n\n'
            f'Set a password for {user.email} with this code: {code}\n\n'
            f'Open {settings.FRONTEND_URL}/activate, enter the code, and choose a new password.\n'
            'The code expires in 24 hours.\n'
        ),
        MailOutbox.Kind.ACTIVATION,
        user,
    )


def account_deactivated_email(user, reason, rejected_pending=False):
    extra = (
        'Your registration was also closed and will not be approved.\n'
        if rejected_pending
        else ''
    )
    send_portal_mail(
        user.email,
        'Dampol 1st NHS account deactivated',
        (
            f'Hello {user.first_name},\n\n'
            'Your school portal account has been deactivated. You cannot sign in.\n'
            f'Reason: {reason}\n'
            f'{extra}'
            'Contact the school office if you need help.\n'
        ),
    )


def account_ready_email(user):
    how = (
        'your LRN and the password you set'
        if user.role == user.Role.STUDENT
        else 'your email and the password you set'
    )
    send_portal_mail(
        user.email,
        'Dampol 1st NHS account ready',
        (
            f'Hello {user.first_name},\n\n'
            f'Your password is set. Sign in at {settings.FRONTEND_URL}/login with {how}.\n'
        ),
    )


DUPLICATE_NOTICE_SUBJECT = 'Dampol 1st NHS: a registration used your details'


def duplicate_registration_message(user):
    """Subject and body telling an account owner that a registration repeated their email or LRN."""
    return (
        DUPLICATE_NOTICE_SUBJECT,
        (
            f'Hello {user.first_name},\n\n'
            'Someone submitted a registration with your email address or LRN. Your account already exists, so no '
            'new account was created.\n\n'
            f'If this was you, sign in at {settings.FRONTEND_URL}/login, or use "Forgot password" there.\n'
            'If it was not you, no action is needed. Tell the school office if it keeps happening.\n'
        ),
    )


def registration_result_message(user, approved, reason=''):
    """Subject and body of the registration result. The outbox queues it; it is not sent here."""
    if approved:
        return (
            'Dampol 1st NHS registration approved',
            (
                f'Hello {user.first_name},\n\n'
                'Your registration was approved. Sign in with your LRN and password.\n'
                f'{settings.FRONTEND_URL}/login\n'
            ),
        )
    return (
        'Dampol 1st NHS registration not approved',
        (
            f'Hello {user.first_name},\n\n'
            'Your registration was not approved.\n'
            f'Reason: {reason}\n'
            'Contact the school office if you need help.\n'
        ),
    )


def password_otp_email(user, code):
    _try_send(
        user.email,
        'Dampol 1st NHS password change code',
        f'Hello {user.first_name},\n\nYour password change code is {code}. It expires in 10 minutes.\n',
        MailOutbox.Kind.CODE,
        user,
    )
