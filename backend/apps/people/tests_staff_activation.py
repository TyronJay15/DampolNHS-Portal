from datetime import timedelta
from unittest import mock

from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts import mail as portal_mail
from apps.accounts import outbox
from apps.accounts.models import MailOutbox, User
from apps.accounts.tests import extract_code

STAFF_URL = '/api/admin/staff/'
STRONG = 'Teacher-pass-2'


class StaffActivationFigureTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@school.test',
            password='admin-pass',
            role=User.Role.ADMIN,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.admin)

    def create_teacher(self, email='ana@school.test'):
        payload = {'first_name': 'Ana', 'last_name': 'Reyes', 'email': email, 'role': 'teacher'}
        return self.client.post(STAFF_URL, payload, format='json')

    def figures(self, email='ana@school.test'):
        rows = self.client.get(STAFF_URL).data
        return next(row['activation'] for row in rows if row['email'] == email)

    def activate(self, email='ana@school.test'):
        code = extract_code(mail.outbox[-1].body)
        payload = {'email': email, 'code': code, 'password': STRONG, 'confirm_password': STRONG}
        return APIClient().post('/api/auth/activate/', payload, format='json')

    def test_a_new_teacher_shows_one_code_sent_and_waiting(self):
        response = self.create_teacher()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['activation_emailed'])
        figures = self.figures()
        self.assertEqual((figures['codes_sent'], figures['attempts'], figures['last_result']), (1, 1, 'sent'))
        self.assertEqual((figures['activated_times'], figures['waiting_days']), (0, 0))

    def test_each_resend_is_counted(self):
        teacher = User.objects.get(pk=self.create_teacher().data['id'])
        for _ in range(2):
            response = self.client.post(f'{STAFF_URL}{teacher.pk}/resend-activation/')
            self.assertTrue(response.data['activation_emailed'])
        self.assertEqual(self.figures()['codes_sent'], 3)

    def test_activation_is_counted_and_ends_the_wait(self):
        self.create_teacher()
        self.assertEqual(self.activate().status_code, 200)
        figures = self.figures()
        self.assertEqual((figures['activated_times'], figures['waiting_days']), (1, None))
        self.assertIsNotNone(figures['activated_at'])

    def test_a_failed_email_is_visible_and_the_account_is_still_created(self):
        with mock.patch.object(portal_mail, 'send_message', side_effect=portal_mail.MailError('server down')):
            response = self.create_teacher()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['activation_emailed'])
        figures = self.figures()
        self.assertEqual((figures['codes_sent'], figures['attempts']), (0, 1))
        self.assertEqual((figures['last_result'], figures['last_error']), ('failed', 'server down'))

    def test_the_log_never_stores_the_code(self):
        self.create_teacher()
        row = MailOutbox.objects.get(kind=MailOutbox.Kind.ACTIVATION)
        self.assertEqual(row.body, '')
        self.assertEqual(row.user.email, 'ana@school.test')

    def test_restoring_a_never_activated_account_sends_and_counts_a_new_code(self):
        teacher = User.objects.get(pk=self.create_teacher().data['id'])
        self.client.post(f'/api/admin/accounts/{teacher.pk}/deactivate/', {'reason': 'Leave'}, format='json')
        response = self.client.post(f'/api/admin/accounts/{teacher.pk}/reactivate/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['activation_emailed'])
        self.activate()
        figures = self.figures()
        self.assertEqual((figures['codes_sent'], figures['activated_times']), (2, 1))

    def test_the_admin_row_has_no_activation_figures(self):
        rows = self.client.get(STAFF_URL).data
        admin_row = next(row for row in rows if row['email'] == 'admin@school.test')
        self.assertIsNone(admin_row['activation'])

    def test_cleanup_keeps_activation_rows_of_live_accounts(self):
        self.create_teacher()
        MailOutbox.objects.update(created_at=timezone.now() - timedelta(days=90))
        self.assertEqual(outbox.prune(), 0)
        self.assertEqual(self.figures()['codes_sent'], 1)

    def test_only_admins_see_the_figures(self):
        teacher = User.objects.create_user(email='t@school.test', password='Strongpass1', role=User.Role.TEACHER)
        other = APIClient()
        other.force_authenticate(user=teacher)
        self.assertEqual(other.get(STAFF_URL).status_code, 403)
