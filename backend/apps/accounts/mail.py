import logging
from html import escape
from smtplib import SMTP, SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

logger = logging.getLogger('apps.accounts.mail')


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
        raise RuntimeError('Mail is using the console backend. Restart Django so SMTP is loaded.')
    if 'smtp' in backend and not (settings.EMAIL_HOST_PASSWORD or '').strip():
        raise RuntimeError('EMAIL_HOST_PASSWORD is missing from backend/.env.')
    return backend


def _login_port():
    host = settings.EMAIL_HOST
    user = settings.EMAIL_HOST_USER
    password = (settings.EMAIL_HOST_PASSWORD or '').strip()
    ports = [settings.EMAIL_PORT]
    if settings.EMAIL_PORT != 2525:
        ports.append(2525)
    last_error = None
    for port in ports:
        try:
            with SMTP(host, port, timeout=settings.EMAIL_TIMEOUT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(user, password)
            return port
        except SMTPAuthenticationError as exc:
            raise RuntimeError(f'SMTP login was rejected ({exc.smtp_code}). Check the Brevo SMTP key.') from exc
        except (OSError, SMTPException) as exc:
            last_error = exc
    raise RuntimeError(f'SMTP could not connect. {last_error}') from last_error


def send_portal_mail(to, subject, body):
    backend = _smtp_ready()
    port = settings.EMAIL_PORT
    if 'smtp' in backend:
        port = _login_port()

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
    try:
        sent = message.send(fail_silently=False)
    except SMTPException as exc:
        logger.exception('SMTP send failed for %s', to)
        code = getattr(exc, 'smtp_code', '')
        raise RuntimeError(f'Mail was rejected for {to}. {code}'.strip()) from exc
    if not sent:
        raise RuntimeError(f'Mail was not accepted for {to}.')
    logger.info('Mail accepted for %s via %s:%s', to, backend, port)
    if 'locmem' not in backend:
        print(f'Mail accepted by Brevo for {to}', flush=True)
    return sent


def _try_send(to, subject, body):
    try:
        send_portal_mail(to, subject, body)
    except Exception:
        logger.exception('Mail skipped for %s; use the code in the Django terminal.', to)


def activation_email(user, code):
    _try_send(
        user.email,
        'Dampol 1st NHS activation code',
        (
            f'Hello {user.first_name},\n\n'
            f'Set a password for {user.email} with this code: {code}\n\n'
            f'Open {settings.FRONTEND_URL}/activate, enter the code, and choose a new password.\n'
            'The code expires in 24 hours.\n'
        ),
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


def registration_result_email(user, approved, reason=''):
    if approved:
        send_portal_mail(
            user.email,
            'Dampol 1st NHS registration approved',
            (
                f'Hello {user.first_name},\n\n'
                'Your registration was approved. Sign in with your LRN and password.\n'
                f'{settings.FRONTEND_URL}/login\n'
            ),
        )
        return
    send_portal_mail(
        user.email,
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
    )
