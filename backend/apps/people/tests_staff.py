from django.core import mail
from rest_framework.test import APITestCase

from apps.accounts.models import User


class StaffAccountTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@school.test',
            password='admin-pass',
            first_name='Ada',
            last_name='Min',
            role=User.Role.ADMIN,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )
        self.teacher_user = User.objects.create_user(
            email='teacher@school.test',
            password='teacher-pass',
            first_name='Tia',
            last_name='Cruz',
            role=User.Role.TEACHER,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )

    def _admin(self):
        login = self.client.post(
            '/api/auth/login/',
            {'identifier': 'admin@school.test', 'password': 'admin-pass'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_admin_creates_teacher_without_password_and_emails_code(self):
        self._admin()
        res = self.client.post(
            '/api/admin/staff/',
            {
                'first_name': 'Ana',
                'last_name': 'Reyes',
                'email': 'ana@school.test',
                'role': 'teacher',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(email='ana@school.test')
        self.assertEqual(user.role, User.Role.TEACHER)
        self.assertEqual(user.account_status, User.AccountStatus.PENDING_ACTIVATION)
        self.assertFalse(user.has_usable_password())
        self.client.credentials()
        login = self.client.post(
            '/api/auth/login/',
            {'identifier': 'ana@school.test', 'password': 'anything'},
            format='json',
        )
        self.assertEqual(login.status_code, 401)
        self.assertEqual(login.data.get('code'), 'account_needs_activation')

    def test_admin_creates_one_head_teacher_only(self):
        self._admin()
        first = self.client.post(
            '/api/admin/staff/',
            {
                'first_name': 'Helen',
                'last_name': 'Cruz',
                'email': 'head@school.test',
                'role': 'head_teacher',
            },
            format='json',
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            '/api/admin/staff/',
            {
                'first_name': 'Other',
                'last_name': 'Head',
                'email': 'head2@school.test',
                'role': 'head_teacher',
            },
            format='json',
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(User.objects.filter(role=User.Role.HEAD_TEACHER).count(), 1)

    def test_staff_list_includes_head_teacher(self):
        User.objects.create_user(
            email='head@school.test',
            password='head-pass',
            first_name='Helen',
            last_name='Cruz',
            role=User.Role.HEAD_TEACHER,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )
        self._admin()
        res = self.client.get('/api/admin/staff/')
        self.assertEqual(res.status_code, 200)
        emails = {row['email'] for row in res.data}
        self.assertIn('head@school.test', emails)
        self.assertIn('teacher@school.test', emails)

    def test_teacher_cannot_create_staff(self):
        login = self.client.post(
            '/api/auth/login/',
            {'identifier': 'teacher@school.test', 'password': 'teacher-pass'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        res = self.client.post(
            '/api/admin/staff/',
            {
                'first_name': 'No',
                'last_name': 'Pe',
                'email': 'nope@school.test',
                'role': 'teacher',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_resend_activation_email(self):
        self._admin()
        created = self.client.post(
            '/api/admin/staff/',
            {
                'first_name': 'Ana',
                'last_name': 'Reyes',
                'email': 'ana2@school.test',
                'role': 'teacher',
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)
        mail.outbox.clear()
        user = User.objects.get(email='ana2@school.test')
        resend = self.client.post(f'/api/admin/staff/{user.id}/resend-activation/', {}, format='json')
        self.assertEqual(resend.status_code, 200, resend.data)
        self.assertEqual(len(mail.outbox), 1)
        blocked = self.client.post(
            f'/api/admin/staff/{self.teacher_user.id}/resend-activation/',
            {},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)
