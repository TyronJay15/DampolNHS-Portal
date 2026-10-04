from unittest import mock

from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts import mail as portal_mail
from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.people import views_admin
from apps.people.models import Registration
from apps.school.models import Program, SchoolYear

URL = '/api/admin/registrations/approve-bulk/'


class BulkApproveTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.g11 = Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11')
        self.g12 = Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12')
        self.admin = User.objects.create_user(email='admin@x.com', password='Strongpass1', role=User.Role.ADMIN)
        self.pending = [self.registration(f'p{index}@x.com', self.g11 if index < 2 else self.g12) for index in range(3)]

    def registration(self, email, program, status=Registration.Status.PENDING):
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
            program=program,
            grade_level_enrollment=program.grade_level,
            status=status,
        )

    def post(self, ids, user=None):
        client = APIClient()
        if user is not False:
            client.force_authenticate(user=user or self.admin)
        return client.post(URL, {'ids': ids}, format='json')

    def test_approves_only_the_listed_pending_registrations(self):
        late = self.registration('late@x.com', self.g11)
        response = self.post([row.pk for row in self.pending])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row['id'] for row in response.data['approved']], [row.pk for row in self.pending])
        for row in self.pending:
            row.refresh_from_db()
            row.user.refresh_from_db()
            self.assertEqual(row.status, Registration.Status.APPROVED)
            self.assertEqual(row.reviewed_by, self.admin)
            self.assertEqual(row.user.approval_status, User.ApprovalStatus.APPROVED)
            self.assertEqual(row.user.account_status, User.AccountStatus.ACTIVE)
        late.refresh_from_db()
        self.assertEqual(late.status, Registration.Status.PENDING)

    def test_same_audit_notification_and_email_as_a_single_approval(self):
        self.post([row.pk for row in self.pending])
        self.assertEqual(AuditLog.objects.filter(action='account_approved').count(), 3)
        summary = AuditLog.objects.get(action='registrations_bulk_approved')
        self.assertEqual(summary.details, {'approved': 3, 'skipped': 0, 'failed': 0})
        for row in self.pending:
            self.assertTrue(Notification.objects.filter(user=row.user, title='Account approved').exists())
        self.assertEqual(len(mail.outbox), 3)

    def test_already_reviewed_are_skipped_and_a_repeat_is_harmless(self):
        done = self.registration('done@x.com', self.g11, Registration.Status.APPROVED)
        rejected = self.registration('no@x.com', self.g11, Registration.Status.REJECTED)
        first = self.post([done.pk, rejected.pk, self.pending[0].pk])
        self.assertEqual([item['id'] for item in first.data['skipped']], [done.pk, rejected.pk])
        self.assertEqual([item['id'] for item in first.data['approved']], [self.pending[0].pk])
        again = self.post([self.pending[0].pk])
        self.assertEqual(again.data['approved'], [])
        self.assertEqual(len(again.data['skipped']), 1)
        rejected.refresh_from_db()
        self.assertEqual(rejected.status, Registration.Status.REJECTED)
        self.assertEqual(AuditLog.objects.filter(action='account_approved').count(), 1)

    def test_one_failure_does_not_block_the_rest(self):
        real = views_admin.approve_registration

        def flaky(registration, actor):
            if registration.pk == self.pending[1].pk:
                raise RuntimeError('boom')
            return real(registration, actor)

        with mock.patch.object(views_admin, 'approve_registration', side_effect=flaky):
            response = self.post([row.pk for row in self.pending])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['approved']], [self.pending[0].pk, self.pending[2].pk])
        self.assertEqual([item['id'] for item in response.data['failed']], [self.pending[1].pk])
        self.pending[1].refresh_from_db()
        self.assertEqual(self.pending[1].status, Registration.Status.PENDING)

    def test_failed_email_is_reported_but_the_student_is_still_approved(self):
        with mock.patch.object(portal_mail, 'send_message', side_effect=portal_mail.MailError('smtp down')):
            response = self.post([self.pending[0].pk])
        self.assertEqual(response.data['emails'], {'failed': 1})
        self.pending[0].refresh_from_db()
        self.assertEqual(self.pending[0].status, Registration.Status.APPROVED)

    def test_only_admins_may_approve_in_bulk(self):
        ids = [self.pending[0].pk]
        for role in (User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.STUDENT):
            other = User.objects.create_user(email=f'{role}@x.com', password='Strongpass1', role=role)
            self.assertEqual(self.post(ids, user=other).status_code, 403, role)
        self.assertEqual(self.post(ids, user=False).status_code, 401)
        self.pending[0].refresh_from_db()
        self.assertEqual(self.pending[0].status, Registration.Status.PENDING)

    def test_bad_input_is_rejected(self):
        self.assertEqual(self.post([]).status_code, 400)
        self.assertEqual(self.post(['1']).status_code, 400)
        self.assertEqual(self.post([True]).status_code, 400)
        self.assertEqual(self.post(list(range(1, 202))).status_code, 400)
        client = APIClient()
        client.force_authenticate(user=self.admin)
        self.assertEqual(client.post(URL, {}, format='json').status_code, 400)

    def test_duplicates_count_once_and_unknown_ids_are_reported(self):
        response = self.post([self.pending[0].pk, self.pending[0].pk, 99999])
        self.assertEqual(len(response.data['approved']), 1)
        self.assertEqual(response.data['failed'], [{'id': 99999, 'detail': 'Registration not found.'}])

    def test_single_approval_still_works(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        ok = client.post(f'/api/admin/registrations/{self.pending[0].pk}/approve/')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data['email_status'], 'sent')
        self.assertEqual(client.post(f'/api/admin/registrations/{self.pending[0].pk}/approve/').status_code, 400)

    def test_approving_students_one_by_one_still_works(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        for row in self.pending:
            response = client.post(f'/api/admin/registrations/{row.pk}/approve/')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual((response.data['status'], response.data['email_status']), ('approved', 'sent'))
            row.user.refresh_from_db()
            self.assertEqual(row.user.account_status, User.AccountStatus.ACTIVE)
            self.assertTrue(Notification.objects.filter(user=row.user, title='Account approved').exists())
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(AuditLog.objects.filter(action='account_approved').count(), 3)

    def test_rejecting_one_student_still_works(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        row = self.pending[0]
        response = client.post(f'/api/admin/registrations/{row.pk}/reject/', {'reason': 'Missing documents'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data['status'], response.data['email_status']), ('rejected', 'sent'))
        self.assertIn('not approved', mail.outbox[0].subject)
        self.assertIn('Missing documents', mail.outbox[0].body)
