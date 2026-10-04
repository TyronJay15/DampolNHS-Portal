from django.core import mail
from rest_framework.test import APITestCase

from apps.accounts.codes import issue_code
from apps.accounts.models import EmailCode, StudentProfile, User


def extract_code(body):
    for token in body.split():
        digits = ''.join(ch for ch in token if ch.isdigit())
        if len(digits) == 6:
            return digits
    raise AssertionError(f'No 6-digit code in email body: {body!r}')


class AuthApiTests(APITestCase):
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
        self.student_user = User.objects.create_user(
            email='student@school.test',
            password='student-pass',
            first_name='Sam',
            last_name='Santos',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )
        StudentProfile.objects.create(user=self.student_user, lrn='111111111111')

    def test_login_uses_credentials_only_no_role(self):
        res = self.client.post(
            '/api/auth/login/',
            {'identifier': 'teacher@school.test', 'password': 'teacher-pass'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['user']['role'], 'teacher')
        self.assertIn('access', res.data)

    def test_logout_revokes_only_that_sessions_refresh_token(self):
        def sign_in():
            return self.client.post(
                '/api/auth/login/',
                {'identifier': 'teacher@school.test', 'password': 'teacher-pass'},
                format='json',
            ).data

        def refresh(token):
            return self.client.post('/api/auth/refresh/', {'refresh': token}, format='json').status_code

        signed_out, other_device = sign_in(), sign_in()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {signed_out["access"]}')
        response = self.client.post('/api/auth/logout/', {'refresh': signed_out['refresh']}, format='json')
        self.assertEqual(response.status_code, 204)
        self.client.credentials()
        self.assertEqual(refresh(signed_out['refresh']), 401)
        self.assertEqual(refresh(other_device['refresh']), 200)

    def test_student_logs_in_with_lrn(self):
        res = self.client.post(
            '/api/auth/login/',
            {'identifier': '111111111111', 'password': 'student-pass'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['user']['role'], 'student')

    def test_login_ignores_role_field_and_uses_account(self):
        res = self.client.post(
            '/api/auth/login/',
            {
                'identifier': 'admin@school.test',
                'password': 'admin-pass',
                'role': 'student',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['user']['role'], 'admin')

    def test_pending_student_cannot_login(self):
        pending = User.objects.create_user(
            email='pending@school.test',
            password='pending-pass',
            first_name='Pat',
            last_name='Pena',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.PENDING,
            account_status=User.AccountStatus.ACTIVE,
        )
        StudentProfile.objects.create(user=pending, lrn='222222222222')
        res = self.client.post(
            '/api/auth/login/',
            {'identifier': '222222222222', 'password': 'pending-pass'},
            format='json',
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data.get('code'), 'account_pending')

    def test_unactivated_staff_cannot_login(self):
        user = User.objects.create_user(
            email='newteacher@school.test',
            password=None,
            first_name='New',
            last_name='Teacher',
            role=User.Role.TEACHER,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.PENDING_ACTIVATION,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        res = self.client.post(
            '/api/auth/login/',
            {'identifier': 'newteacher@school.test', 'password': 'anything'},
            format='json',
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data.get('code'), 'account_needs_activation')

    def test_wrong_password(self):
        res = self.client.post(
            '/api/auth/login/',
            {'identifier': 'teacher@school.test', 'password': 'nope'},
            format='json',
        )
        self.assertEqual(res.status_code, 401)

    def test_change_password_requires_email_otp(self):
        login = self.client.post(
            '/api/auth/login/',
            {'identifier': 'student@school.test', 'password': 'student-pass'},
            format='json',
        )
        token = login.data['access']
        otp = self.client.post(
            '/api/auth/change-password/otp/',
            {'current_password': 'student-pass'},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(otp.status_code, 200, otp.data)
        self.assertTrue(mail.outbox)
        code = extract_code(mail.outbox[-1].body)
        rejected = self.client.post(
            '/api/auth/change-password/verify/',
            {'current_password': 'student-pass', 'code': '000000'},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(rejected.status_code, 400)
        verified = self.client.post(
            '/api/auth/change-password/verify/',
            {'current_password': 'student-pass', 'code': code},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(verified.status_code, 200, verified.data)
        missing = self.client.post(
            '/api/auth/change-password/',
            {
                'current_password': 'student-pass',
                'new_password': 'student-pass-2',
                'confirm_password': 'student-pass-2',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(missing.status_code, 400)
        changed = self.client.post(
            '/api/auth/change-password/',
            {
                'current_password': 'student-pass',
                'new_password': 'student-pass-2',
                'confirm_password': 'student-pass-2',
                'code': code,
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(changed.status_code, 200, changed.data)
        again = self.client.post(
            '/api/auth/login/',
            {'identifier': '111111111111', 'password': 'student-pass-2'},
            format='json',
        )
        self.assertEqual(again.status_code, 200, again.data)

    def test_forgot_password_sends_code_without_current_password(self):
        otp = self.client.post(
            '/api/auth/forgot-password/otp/',
            {'identifier': 'teacher@school.test'},
            format='json',
        )
        self.assertEqual(otp.status_code, 200, otp.data)
        unknown = self.client.post(
            '/api/auth/forgot-password/otp/',
            {'identifier': 'missing@school.test'},
            format='json',
        )
        self.assertEqual(unknown.status_code, 200)
        code = extract_code(mail.outbox[-1].body)
        rejected = self.client.post(
            '/api/auth/forgot-password/verify/',
            {'identifier': 'teacher@school.test', 'code': '000000'},
            format='json',
        )
        self.assertEqual(rejected.status_code, 400)
        verified = self.client.post(
            '/api/auth/forgot-password/verify/',
            {'identifier': 'teacher@school.test', 'code': code},
            format='json',
        )
        self.assertEqual(verified.status_code, 200, verified.data)
        changed = self.client.post(
            '/api/auth/forgot-password/',
            {
                'identifier': 'teacher@school.test',
                'new_password': 'teacher-pass-9',
                'confirm_password': 'teacher-pass-9',
                'code': code,
            },
            format='json',
        )
        self.assertEqual(changed.status_code, 200, changed.data)

    def test_activate_staff_account(self):
        user = User.objects.create_user(
            email='activate@school.test',
            password=None,
            first_name='Act',
            last_name='Ive',
            role=User.Role.TEACHER,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.PENDING_ACTIVATION,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        code = issue_code(user, EmailCode.Purpose.ACTIVATE)
        res = self.client.post(
            '/api/auth/activate/',
            {
                'email': 'activate@school.test',
                'code': code,
                'password': 'ready-pass-1',
                'confirm_password': 'ready-pass-1',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        user.refresh_from_db()
        self.assertEqual(user.account_status, User.AccountStatus.ACTIVE)
        self.assertTrue(user.has_usable_password())
        self.assertTrue(mail.outbox)
        login = self.client.post(
            '/api/auth/login/',
            {'identifier': 'activate@school.test', 'password': 'ready-pass-1'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(EmailCode.objects.filter(user=user, used_at__isnull=False).count(), 1)


class PasswordCodeSafetyTests(APITestCase):
    """Resend waits RESEND_SECONDS; MAX_ATTEMPTS wrong guesses cancel a code."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='teacher@school.test',
            password='teacher-pass',
            role=User.Role.TEACHER,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)

    def _send(self):
        return self.client.post('/api/auth/change-password/otp/', {'current_password': 'teacher-pass'}, format='json')

    def _verify(self, code):
        return self.client.post(
            '/api/auth/change-password/verify/', {'current_password': 'teacher-pass', 'code': code}, format='json'
        )

    def test_resend_must_wait(self):
        first = self._send()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['resend_in'], 60)
        again = self._send()
        self.assertEqual(again.status_code, 429)
        self.assertIn('wait', again.data['detail'])
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_works_after_the_wait(self):
        from datetime import timedelta

        from django.utils import timezone

        self._send()
        EmailCode.objects.update(created_at=timezone.now() - timedelta(seconds=61))
        self.assertEqual(self._send().status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_too_many_wrong_guesses_cancel_the_code(self):
        self._send()
        code = extract_code(mail.outbox[-1].body)
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(5):
            self.assertEqual(self._verify(wrong).status_code, 400)
        self.assertEqual(self._verify(code).status_code, 400)

    def test_forgot_password_cooldown_stays_silent(self):
        self.client.force_authenticate(user=None)
        body = {'identifier': 'teacher@school.test'}
        first = self.client.post('/api/auth/forgot-password/otp/', body, format='json')
        second = self.client.post('/api/auth/forgot-password/otp/', body, format='json')
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(first.data['detail'], second.data['detail'])
        self.assertEqual(len(mail.outbox), 1)
