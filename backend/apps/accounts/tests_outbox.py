from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import mail as portal_mail
from apps.accounts import outbox
from apps.accounts.models import MailOutbox, User
from apps.audit.models import AuditLog
from apps.people.models import Registration
from apps.school.models import Program, SchoolYear

BACKGROUND = override_settings(MAIL_DELIVERY='background')


class OutboxFixture(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.program = Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11')
        self.admin = User.objects.create_user(email='admin@x.com', password='Strongpass1', role=User.Role.ADMIN)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def registration(self, email):
        user = User.objects.create_user(
            email=email,
            password='Strongpass1',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.PENDING,
            account_status=User.AccountStatus.PENDING_ACTIVATION,
        )
        return Registration.objects.create(
            user=user,
            school_year=self.year,
            program=self.program,
            grade_level_enrollment='Grade 11',
        )

    def approve(self, registration):
        return self.client.post(f'/api/admin/registrations/{registration.pk}/approve/')

    def approve_all(self, rows):
        return self.client.post('/api/admin/registrations/approve-bulk/', {'ids': [row.pk for row in rows]}, format='json')

    def row(self, registration):
        return MailOutbox.objects.get(registration=registration)


@BACKGROUND
class BackgroundDeliveryTests(OutboxFixture):
    def test_approval_queues_the_email_and_the_sender_sends_it(self):
        student = self.registration('a@x.com')
        response = self.approve(student)
        self.assertEqual(response.data['email_status'], 'queued')
        self.assertEqual(len(mail.outbox), 0)
        call_command('send_outbox', stdout=mock.Mock())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('approved', mail.outbox[0].subject)
        row = self.row(student)
        self.assertEqual((row.status, row.attempts, row.body), ('sent', 1, ''))

    def test_bulk_approval_returns_without_waiting_for_the_mail_server(self):
        rows = [self.registration(f's{index}@x.com') for index in range(5)]
        with mock.patch.object(portal_mail, 'send_message') as send:
            response = self.approve_all(rows)
        send.assert_not_called()
        self.assertEqual(response.data['emails'], {'queued': 5})
        self.assertEqual(MailOutbox.objects.filter(status='queued').count(), 5)

    def test_every_approved_student_has_an_email_even_if_the_sender_never_runs(self):
        rows = [self.registration(f's{index}@x.com') for index in range(3)]
        self.approve_all(rows)
        for registration in rows:
            registration.refresh_from_db()
            self.assertEqual(registration.status, Registration.Status.APPROVED)
            self.assertTrue(MailOutbox.objects.filter(registration=registration, status='queued').exists())

    def test_a_temporary_failure_is_retried_then_marked_failed(self):
        student = self.registration('a@x.com')
        self.approve(student)
        error = portal_mail.MailError('server busy')
        with mock.patch.object(portal_mail, 'send_message', side_effect=error):
            for attempt in range(1, outbox.MAX_ATTEMPTS + 1):
                outbox.run_once()
                row = self.row(student)
                self.assertEqual(row.attempts, attempt)
                if attempt < outbox.MAX_ATTEMPTS:
                    self.assertEqual(row.status, 'queued')
                    self.assertGreater(row.next_attempt_at, timezone.now())
                    MailOutbox.objects.filter(pk=row.pk).update(next_attempt_at=timezone.now())
        self.assertEqual((row.status, row.last_error), ('failed', 'server busy'))

    def test_a_refused_address_fails_at_once(self):
        student = self.registration('a@x.com')
        self.approve(student)
        refused = portal_mail.MailError('refused', permanent=True)
        with mock.patch.object(portal_mail, 'send_message', side_effect=refused):
            outbox.run_once()
        self.assertEqual((self.row(student).status, self.row(student).attempts), ('failed', 1))

    def test_resend_queues_failed_emails_again_and_is_audited(self):
        student = self.registration('a@x.com')
        self.approve(student)
        MailOutbox.objects.filter(registration=student).update(status='failed', attempts=5, last_error='x')
        response = self.client.post('/api/admin/registrations/emails/resend/')
        self.assertEqual((response.data['resent'], response.data['failed'], response.data['queued']), (1, 0, 1))
        self.assertEqual((self.row(student).status, self.row(student).attempts), ('queued', 0))
        self.assertTrue(AuditLog.objects.filter(action='registration_emails_resent').exists())

    @override_settings(MAIL_DAILY_LIMIT=5, MAIL_CODE_RESERVE=2)
    def test_notices_stop_at_the_daily_allowance_and_the_rest_wait(self):
        rows = [self.registration(f's{index}@x.com') for index in range(5)]
        response = self.approve_all(rows)
        self.assertEqual(response.data['emails'], {'queued': 3, 'waiting': 2})
        self.assertEqual(outbox.run_once()['sent'], 3)
        summary = self.client.get('/api/admin/registrations/emails/').data
        self.assertEqual((summary['waiting'], summary['notice_left'], summary['used_today']), (2, 0, 3))
        listed = self.client.get('/api/admin/registrations/?status=approved').data['results']
        states = sorted(row['email_delivery']['state'] for row in listed)
        self.assertEqual(states, ['sent', 'sent', 'sent', 'waiting', 'waiting'])

    @override_settings(MAIL_DAILY_LIMIT=5, MAIL_CODE_RESERVE=2)
    def test_codes_still_send_when_notices_are_used_up_and_are_counted_without_their_body(self):
        rows = [self.registration(f's{index}@x.com') for index in range(3)]
        self.approve_all(rows)
        outbox.run_once()
        portal_mail.activation_email(rows[0].user, '123456')
        self.assertEqual(len(mail.outbox), 4)
        code_row = MailOutbox.objects.get(kind='activation')
        self.assertEqual((code_row.status, code_row.body), ('sent', ''))
        self.assertEqual(outbox.used_today(), 4)

    def test_a_send_left_behind_by_a_dead_sender_is_picked_up_again(self):
        student = self.registration('a@x.com')
        self.approve(student)
        MailOutbox.objects.filter(registration=student).update(
            status='sending',
            claimed_at=timezone.now() - outbox.STALE_CLAIM - timedelta(minutes=1),
        )
        outbox.run_once()
        self.assertEqual(self.row(student).status, 'sent')

    def test_old_finished_rows_are_removed(self):
        student = self.registration('a@x.com')
        self.approve(student)
        outbox.run_once()
        MailOutbox.objects.update(created_at=timezone.now() - timedelta(days=31))
        self.assertEqual(outbox.prune(), 1)
        self.assertFalse(MailOutbox.objects.exists())


class InlineDeliveryTests(OutboxFixture):
    def test_inline_mode_sends_right_after_saving(self):
        student = self.registration('a@x.com')
        response = self.approve(student)
        self.assertEqual(response.data['email_status'], 'sent')
        self.assertEqual(len(mail.outbox), 1)

    def test_an_inline_failure_is_final_and_can_be_resent(self):
        student = self.registration('a@x.com')
        with mock.patch.object(portal_mail, 'send_message', side_effect=portal_mail.MailError('down')):
            response = self.approve(student)
        self.assertEqual(response.data['email_status'], 'failed')
        listed = self.client.get('/api/admin/registrations/?status=approved').data['results'][0]
        self.assertEqual(listed['email_delivery'], {'state': 'failed', 'error': 'down'})
        self.client.post('/api/admin/registrations/emails/resend/')
        self.assertEqual(self.row(student).status, 'sent')
        self.assertEqual(len(mail.outbox), 1)


class EndpointAccessTests(OutboxFixture):
    def test_only_admins_see_the_delivery_strip_or_resend(self):
        for role in (User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.STUDENT):
            other = APIClient()
            other.force_authenticate(user=User.objects.create_user(email=f'{role}@x.com', password='Strongpass1', role=role))
            self.assertEqual(other.get('/api/admin/registrations/emails/').status_code, 403, role)
            self.assertEqual(other.post('/api/admin/registrations/emails/resend/').status_code, 403, role)
        self.assertEqual(APIClient().get('/api/admin/registrations/emails/').status_code, 401)
