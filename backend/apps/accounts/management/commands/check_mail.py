"""Report the mail setup without printing secrets, and optionally send one test message."""

from smtplib import SMTP, SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.mail import send_portal_mail


class Command(BaseCommand):
    help = 'Check the Brevo mail setup (SMTP login or HTTPS API key) and optionally send a test. Never prints keys.'

    def add_arguments(self, parser):
        parser.add_argument('--to', default='', help='Optional address for a one-off test message.')

    def handle(self, *args, **options):
        self.stdout.write(f'Transport: {settings.MAIL_TRANSPORT}')
        self.stdout.write(f'From: {settings.DEFAULT_FROM_EMAIL}')
        if settings.MAIL_TRANSPORT == 'brevo_api':
            self.stdout.write(f'API key loaded: {"yes" if settings.BREVO_API_KEY else "no"}')
        else:
            self._check_smtp_login()

        target = (options['to'] or '').strip()
        if not target:
            return
        send_portal_mail(
            target,
            'Dampol 1st NHS mail check',
            'This is a portal mail check. If you received it, mail delivery is working.',
        )
        self.stdout.write(self.style.SUCCESS(f'Test accepted for {target}'))

    def _check_smtp_login(self):
        host = settings.EMAIL_HOST
        user = settings.EMAIL_HOST_USER
        password = (settings.EMAIL_HOST_PASSWORD or '').strip()
        ports = [settings.EMAIL_PORT]
        if settings.EMAIL_PORT != 2525:
            ports.append(2525)

        self.stdout.write(f'Host: {host}')
        self.stdout.write(f'Login: {user}')
        self.stdout.write(f'Key loaded: {"yes" if password else "no"} ({len(password)} chars)')

        last_error = ''
        for port in ports:
            try:
                with SMTP(host, port, timeout=20) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(user, password)
                self.stdout.write(self.style.SUCCESS(f'Login ok on port {port}'))
                return
            except SMTPAuthenticationError as exc:
                last_error = f'{exc.smtp_code} {exc.smtp_error}'
                self.stderr.write(self.style.ERROR(f'Auth failed on {port}: {last_error}'))
                break
            except (OSError, SMTPException) as exc:
                last_error = str(exc)
                self.stderr.write(self.style.WARNING(f'Port {port} failed: {exc}'))
        raise SystemExit(f'SMTP login failed. {last_error}')
