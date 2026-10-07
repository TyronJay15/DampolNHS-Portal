"""Authenticator app for Admin and Head Teacher (security plan W3, W7): set-up, sign-in, wrong codes, replay,
recovery codes, turning it off, resets, and the maintenance console."""

import time
from io import StringIO

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework.test import APIClient

from apps.accounts import mfa
from apps.accounts.models import AuthenticatorDevice, AuthSession, RecoveryCode, User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification

PASSWORD = 'Strongpass1!'
COOKIE = settings.AUTH_REFRESH_COOKIE


def make_user(email, role):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        role=role,
        approval_status=User.ApprovalStatus.APPROVED,
        account_status=User.AccountStatus.ACTIVE,
    )


def code_for(user, offset=0):
    """The code the person's phone shows now (offset in 30-second steps)."""
    device = AuthenticatorDevice.objects.get(user=user)
    totp = TOTP(mfa._decrypt(device), step=30, t0=0, digits=6, drift=offset)
    totp.time = time.time()
    return f'{totp.token():06d}'


@override_settings(MFA_ENFORCED=True)
class MfaFixture(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user('admin@x.com', User.Role.ADMIN)
        self.head = make_user('head@x.com', User.Role.HEAD_TEACHER)
        self.teacher = make_user('t@x.com', User.Role.TEACHER)

    def password_step(self, email):
        client = APIClient()
        return client, client.post('/api/auth/login/', {'identifier': email, 'password': PASSWORD}, format='json')

    def enroll(self, user):
        secret, _uri, _svg = mfa.start_enrollment(user)
        device = AuthenticatorDevice.objects.get(user=user)
        totp = TOTP(mfa._decrypt(device), step=30, t0=0, digits=6)
        totp.time = time.time()
        codes = mfa.confirm_enrollment(user, f'{totp.token():06d}')
        # The set-up code used the current step; the next sign-in needs a later one.
        AuthenticatorDevice.objects.filter(user=user).update(last_t=-1)
        return secret, codes


class EnrollmentTests(MfaFixture):
    def test_a_privileged_account_must_set_up_the_app_before_anything_signs_in(self):
        client, response = self.password_step('admin@x.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['mfa'], 'enroll')
        self.assertNotIn('access', response.data)
        self.assertNotIn(COOKIE, response.cookies)
        self.assertFalse(AuthSession.objects.exists())

        start = client.post('/api/auth/mfa/enroll/', {'challenge': response.data['challenge']}, format='json')
        self.assertEqual(start.status_code, 200)
        self.assertIn('<svg', start.data['qr_svg'])
        self.assertTrue(start.data['otpauth_uri'].startswith('otpauth://totp/'))
        wrong = client.post('/api/auth/mfa/enroll/confirm/', {'challenge': response.data['challenge'], 'code': '000000'}, format='json')
        self.assertEqual(wrong.status_code, 400)

        AuthenticatorDevice.objects.filter(user=self.admin).update(throttling_failure_count=0, throttling_failure_timestamp=None)
        done = client.post(
            '/api/auth/mfa/enroll/confirm/', {'challenge': response.data['challenge'], 'code': code_for(self.admin)}, format='json'
        )
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(len(done.data['recovery_codes']), mfa.RECOVERY_CODE_COUNT)
        self.assertIn('access', done.data)
        self.assertTrue(done.cookies[COOKIE]['httponly'])
        self.assertTrue(AuditLog.objects.filter(action='mfa_enrolled', target_id=str(self.admin.pk)).exists())

    def test_the_secret_is_stored_encrypted(self):
        secret, _codes = self.enroll(self.admin)
        stored = AuthenticatorDevice.objects.get(user=self.admin).secret
        self.assertNotIn(secret, stored)
        self.assertNotIn(secret.lower(), stored.lower())

    def test_recovery_codes_are_stored_only_as_hashes(self):
        _secret, codes = self.enroll(self.admin)
        stored = list(RecoveryCode.objects.values_list('code_hash', flat=True))
        for code in codes:
            self.assertNotIn(code, stored)
            self.assertNotIn(code.replace('-', ''), stored)

    def test_teachers_and_students_are_not_asked(self):
        _client, response = self.password_step('t@x.com')
        self.assertIn('access', response.data)

    @override_settings(MFA_ENFORCED=False)
    def test_with_enforcement_paused_an_enrolled_account_still_needs_its_code(self):
        self.enroll(self.head)
        _client, response = self.password_step('head@x.com')
        self.assertEqual(response.data['mfa'], 'verify')
        _client, response = self.password_step('admin@x.com')  # not enrolled: allowed in while paused
        self.assertIn('access', response.data)


class SignInTests(MfaFixture):
    def setUp(self):
        super().setUp()
        _secret, self.codes = self.enroll(self.admin)

    def challenge(self):
        client, response = self.password_step('admin@x.com')
        self.assertEqual(response.data['mfa'], 'verify')
        return client, response.data['challenge']

    def test_the_right_code_signs_in(self):
        client, challenge = self.challenge()
        response = client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': code_for(self.admin)}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
        self.assertIn(COOKIE, response.cookies)

    def test_a_code_cannot_be_used_twice(self):
        client, challenge = self.challenge()
        code = code_for(self.admin)
        self.assertEqual(client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': code}, format='json').status_code, 200)
        again, challenge = self.challenge()
        replay = again.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': code}, format='json')
        self.assertEqual(replay.status_code, 400)

    def test_wrong_codes_make_the_next_try_wait(self):
        client, challenge = self.challenge()
        first = client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': '000000'}, format='json')
        self.assertEqual(first.status_code, 400)
        second = client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': code_for(self.admin)}, format='json')
        self.assertEqual((second.status_code, second.data['code']), (429, 'mfa_wait'))

    def test_a_recovery_code_works_once(self):
        client, challenge = self.challenge()
        recovery = self.codes[0]
        self.assertEqual(client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': recovery}, format='json').status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action='mfa_recovery_used').exists())
        again, challenge = self.challenge()
        self.assertEqual(again.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': recovery}, format='json').status_code, 400)
        self.assertEqual(mfa.recovery_codes_left(self.admin), mfa.RECOVERY_CODE_COUNT - 1)

    def test_a_tampered_or_old_challenge_is_refused(self):
        client, challenge = self.challenge()
        tampered = client.post('/api/auth/mfa/verify/', {'challenge': challenge + 'x', 'code': code_for(self.admin)}, format='json')
        self.assertEqual(tampered.data['code'], 'challenge_invalid')
        enroll_purpose = mfa.issue_challenge(self.admin, mfa.ENROLL)
        wrong_purpose = client.post('/api/auth/mfa/verify/', {'challenge': enroll_purpose, 'code': code_for(self.admin)}, format='json')
        self.assertEqual(wrong_purpose.data['code'], 'challenge_invalid')

    def test_a_password_change_voids_a_waiting_challenge(self):
        client, challenge = self.challenge()
        self.admin.set_password('Changed-pass-77')
        self.admin.save(update_fields=['password'])
        response = client.post('/api/auth/mfa/verify/', {'challenge': challenge, 'code': code_for(self.admin)}, format='json')
        self.assertEqual(response.data['code'], 'challenge_invalid')


class ChangeTests(MfaFixture):
    def setUp(self):
        super().setUp()
        self.enroll(self.head)
        self.client = APIClient()
        self.client.force_authenticate(self.head)

    def test_new_recovery_codes_need_the_password_and_a_code(self):
        bad = self.client.post('/api/auth/mfa/recovery-codes/', {'password': 'nope', 'code': code_for(self.head)}, format='json')
        self.assertEqual(bad.data['code'], 'password_invalid')
        good = self.client.post('/api/auth/mfa/recovery-codes/', {'password': PASSWORD, 'code': code_for(self.head)}, format='json')
        self.assertEqual(len(good.data['recovery_codes']), mfa.RECOVERY_CODE_COUNT)

    def test_turning_it_off_needs_the_password_and_a_code(self):
        response = self.client.post('/api/auth/mfa/disable/', {'password': PASSWORD, 'code': code_for(self.head)}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthenticatorDevice.objects.filter(user=self.head).exists())
        self.assertTrue(AuditLog.objects.filter(action='mfa_disabled').exists())
        _client, login = self.password_step('head@x.com')
        self.assertEqual(login.data['mfa'], 'enroll')  # still required, so set-up comes back

    def test_status_shows_what_the_account_has(self):
        response = self.client.get('/api/auth/mfa/')
        self.assertEqual(response.data, {'enrolled': True, 'required': True, 'eligible': True, 'recovery_codes_left': 10})


class ResetTests(MfaFixture):
    def test_an_admin_resets_another_persons_app_and_signs_them_out(self):
        self.enroll(self.head)
        AuthSession.objects.create(user=self.head, expires_at=timezone.now() + timezone.timedelta(hours=1))
        admin = APIClient()
        admin.force_authenticate(self.admin)
        response = admin.post(f'/api/admin/accounts/{self.head.pk}/reset-authenticator/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthenticatorDevice.objects.filter(user=self.head).exists())
        self.assertFalse(AuthSession.objects.filter(user=self.head, ended_at=None).exists())
        self.assertTrue(AuditLog.objects.filter(action='mfa_reset', target_id=str(self.head.pk)).exists())
        own = admin.post(f'/api/admin/accounts/{self.admin.pk}/reset-authenticator/')
        self.assertEqual(own.status_code, 400)

    def test_only_an_admin_can_reset(self):
        head = APIClient()
        head.force_authenticate(self.head)
        self.assertEqual(head.post(f'/api/admin/accounts/{self.admin.pk}/reset-authenticator/').status_code, 403)

    def test_the_break_glass_command_resets_and_audits(self):
        self.enroll(self.admin)
        call_command('reset_authenticator', 'admin@x.com', stdout=StringIO())
        self.assertFalse(AuthenticatorDevice.objects.filter(user=self.admin).exists())
        entry = AuditLog.objects.get(action='mfa_reset')
        self.assertEqual(entry.details['by'], 'server command')


class ConsoleTests(MfaFixture):
    def test_the_console_needs_the_authenticator_code_too(self):
        call_command('console_access', '--maintenance', 'admin@x.com', stdout=StringIO())
        self.enroll(self.admin)
        path = f'/{settings.DJANGO_ADMIN_PATH}/login/'
        without_code = self.client.post(path, {'username': 'admin@x.com', 'password': PASSWORD})
        self.assertNotEqual(without_code.status_code, 302)
        device = AuthenticatorDevice.objects.get(user=self.admin)
        with_code = self.client.post(
            path,
            {'username': 'admin@x.com', 'password': PASSWORD, 'otp_device': device.persistent_id, 'otp_token': code_for(self.admin)},
        )
        self.assertEqual(with_code.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action='django_admin_login').exists())
        self.assertTrue(Notification.objects.filter(category='security', title='Maintenance console sign-in').exists())

    def test_sensitive_records_are_read_only_in_the_console(self):
        from django.contrib import admin as django_admin

        from apps.grading.models import Grade
        from apps.people.models import Registration

        request = type('Request', (), {'user': self.admin})()
        for model in (User, Grade, Registration, AuditLog):
            model_admin = django_admin.site._registry[model]
            self.assertFalse(model_admin.has_change_permission(request), model)
            self.assertFalse(model_admin.has_delete_permission(request), model)
            self.assertFalse(model_admin.has_add_permission(request), model)

    def test_console_access_levels_are_set_by_the_server_command(self):
        call_command('console_access', '--content-editor', 'head@x.com', stdout=StringIO())
        self.head.refresh_from_db()
        self.assertTrue(self.head.is_staff)
        self.assertFalse(self.head.is_superuser)
        self.assertTrue(self.head.has_perm('chatbot.change_faqentry'))
        self.assertFalse(self.head.has_perm('grading.change_grade'))
        call_command('console_access', '--revoke', 'head@x.com', stdout=StringIO())
        self.head.refresh_from_db()
        self.assertFalse(self.head.is_staff)
