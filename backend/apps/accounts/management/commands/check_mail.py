"""Report SMTP login/port status without printing secrets."""

from smtplib import SMTP, SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Check Brevo SMTP login and optional test send. Does not print the SMTP key.'

    def add_arguments(self, parser):
        parser.add_argument('--to', default='', help='Optional address for a one-off test message.')

    def handle(self, *args, **options):
        host = settings.EMAIL_HOST
        user = settings.EMAIL_HOST_USER
        password = (settings.EMAIL_HOST_PASSWORD or '').strip()
        sender = settings.DEFAULT_FROM_EMAIL
        ports = [settings.EMAIL_PORT]
        if settings.EMAIL_PORT != 2525:
            ports.append(2525)

        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Host: {host}')
        self.stdout.write(f'Login: {user}')
        self.stdout.write(f'From: {sender}')
        self.stdout.write(f'Key loaded: {"yes" if password else "no"} ({len(password)} chars)')

        working_port = None
        last_error = ''
        for port in ports:
            try:
                with SMTP(host, port, timeout=20) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(user, password)
                working_port = port
                self.stdout.write(self.style.SUCCESS(f'Login ok on port {port}'))
                break
            except SMTPAuthenticationError as exc:
                last_error = f'{exc.smtp_code} {exc.smtp_error}'
                self.stderr.write(self.style.ERROR(f'Auth failed on {port}: {last_error}'))
                break
            except (OSError, SMTPException) as exc:
                last_error = str(exc)
                self.stderr.write(self.style.WARNING(f'Port {port} failed: {exc}'))

        if working_port is None:
            raise SystemExit(f'SMTP login failed. {last_error}')

        target = (options['to'] or '').strip()
        if not target:
            return

        from apps.accounts.mail import send_portal_mail

        send_portal_mail(
            target,
            'Dampol 1st NHS mail check',
            'This is a portal mail check. If you received it, SMTP delivery is working.',
        )
        self.stdout.write(self.style.SUCCESS(f'Test accepted for {target}'))
