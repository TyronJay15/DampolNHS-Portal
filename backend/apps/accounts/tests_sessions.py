"""Sign-in sessions (security plan W1, W6, W19): cookies, rotation, replay detection, time limits, revocation, CSRF."""

from datetime import timedelta
from io import StringIO

import jwt
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import sessions
from apps.accounts.codes import issue_code
from apps.accounts.lifecycle import archive_account
from apps.accounts.models import AuthSession, SessionToken, StudentProfile, User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification

PASSWORD = 'Strongpass1!'
COOKIE = settings.AUTH_REFRESH_COOKIE


def make_user(email, role=User.Role.TEACHER):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name='Tia',
        last_name='Cruz',
        role=role,
        approval_status=User.ApprovalStatus.APPROVED,
        account_status=User.AccountStatus.ACTIVE,
    )


class SessionFixture(TestCase):
    def setUp(self):
        cache.clear()
        self.teacher = make_user('t@x.com')
        self.admin = make_user('admin@x.com', User.Role.ADMIN)

    def sign_in(self, email='t@x.com'):
        device = APIClient()
        response = device.post('/api/auth/login/', {'identifier': email, 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        device.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        return device, response

    @staticmethod
    def age(session, **delta):
        AuthSession.objects.filter(pk=session.pk).update(last_refreshed_at=timezone.now() - timedelta(**delta))


class CookieTests(SessionFixture):
    def test_the_refresh_token_is_only_in_a_protected_cookie(self):
        _device, response = self.sign_in()
        self.assertNotIn('refresh', response.data)
        cookie = response.cookies[COOKIE]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['path'], '/api/auth/')
        self.assertEqual(cookie['samesite'], settings.AUTH_COOKIE_SAMESITE)
        self.assertEqual(cookie['domain'], '')  # host-only
        self.assertEqual(cookie['max-age'], '')  # ends with the browser
        self.assertEqual(len(cookie.value), 43)

    def test_the_access_token_carries_ids_only_and_lasts_fifteen_minutes(self):
        _device, response = self.sign_in()
        claims = jwt.decode(response.data['access'], options={'verify_signature': False})
        self.assertEqual(set(claims), {'token_type', 'exp', 'iat', 'jti', 'user_id', 'sid'})
        self.assertAlmostEqual(claims['exp'] - claims['iat'], settings.AUTH_ACCESS_MINUTES * 60, delta=2)

    def test_only_a_hash_of_each_refresh_token_is_stored(self):
        _device, response = self.sign_in()
        raw = response.cookies[COOKIE].value
        self.assertFalse(SessionToken.objects.filter(token_hash=raw).exists())
        self.assertTrue(SessionToken.objects.filter(token_hash=sessions._hash(raw)).exists())


class RotationTests(SessionFixture):
    def test_refresh_rotates_and_restores_the_sign_in_after_a_reload(self):
        device, login = self.sign_in()
        first = login.cookies[COOKIE].value
        response = device.post('/api/auth/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['email'], 't@x.com')
        self.assertNotEqual(response.cookies[COOKIE].value, first)

    def test_a_used_token_inside_the_grace_window_is_a_conflict_not_theft(self):
        device, login = self.sign_in()
        old = login.cookies[COOKIE].value
        device.post('/api/auth/refresh/')
        racer = APIClient()
        racer.cookies[COOKIE] = old
        self.assertEqual(racer.post('/api/auth/refresh/').status_code, 409)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 200)

    def test_a_stolen_token_coming_back_ends_the_whole_sign_in(self):
        device, login = self.sign_in()
        stolen = login.cookies[COOKIE].value
        device.post('/api/auth/refresh/')
        SessionToken.objects.exclude(used_at=None).update(used_at=timezone.now() - timedelta(minutes=5))
        thief = APIClient()
        thief.cookies[COOKIE] = stolen
        self.assertEqual(thief.post('/api/auth/refresh/').status_code, 401)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)  # the real browser is out too
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)  # and so is its access token
        self.assertEqual(AuthSession.objects.get().end_reason, AuthSession.EndReason.REPLAY)
        self.assertTrue(AuditLog.objects.filter(action='session_replay_detected').exists())
        self.assertTrue(Notification.objects.filter(user=self.admin, category='security').exists())

    def test_an_unknown_or_missing_cookie_is_refused(self):
        stranger = APIClient()
        self.assertEqual(stranger.post('/api/auth/refresh/').status_code, 401)
        stranger.cookies[COOKIE] = 'made-up'
        self.assertEqual(stranger.post('/api/auth/refresh/').status_code, 401)


class TimeLimitTests(SessionFixture):
    def test_thirty_minutes_without_a_refresh_ends_the_sign_in(self):
        device, _login = self.sign_in()
        self.age(AuthSession.objects.get(), minutes=settings.AUTH_IDLE_MINUTES + 1)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)
        self.assertEqual(AuthSession.objects.get().end_reason, AuthSession.EndReason.IDLE)

    def test_activity_keeps_the_sign_in_within_the_idle_limit(self):
        device, _login = self.sign_in()
        self.age(AuthSession.objects.get(), minutes=settings.AUTH_IDLE_MINUTES - 1)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 200)

    def test_twelve_hours_is_the_limit_even_for_an_active_user(self):
        device, _login = self.sign_in()
        AuthSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)

    def test_an_access_token_never_outlives_the_session(self):
        _device, login = self.sign_in()
        session = AuthSession.objects.get()
        session.expires_at = timezone.now() + timedelta(minutes=2)
        session.save(update_fields=['expires_at'])
        claims = jwt.decode(sessions.access_token(session), options={'verify_signature': False})
        self.assertLessEqual(claims['exp'], int(session.expires_at.timestamp()) + 1)


class RevocationTests(SessionFixture):
    def test_logout_ends_the_session_and_its_access_token(self):
        device, _login = self.sign_in()
        response = device.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[COOKIE].value, '')
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)
        self.assertEqual(AuthSession.objects.get().end_reason, AuthSession.EndReason.LOGOUT)

    def test_changing_the_password_signs_out_every_other_device(self):
        here, _login = self.sign_in()
        elsewhere, _other = self.sign_in()
        code = issue_code(self.teacher, 'password', minutes=10)
        response = here.post(
            '/api/auth/change-password/',
            {'current_password': PASSWORD, 'code': code, 'new_password': 'Another-pass-42', 'confirm_password': 'Another-pass-42'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(here.get('/api/auth/me/').status_code, 200)
        self.assertEqual(elsewhere.get('/api/auth/me/').status_code, 401)
        self.assertEqual(elsewhere.post('/api/auth/refresh/').status_code, 401)

    def test_a_password_reset_signs_out_everywhere(self):
        device, _login = self.sign_in()
        code = issue_code(self.teacher, 'password', minutes=10)
        response = APIClient().post(
            '/api/auth/forgot-password/',
            {'identifier': 't@x.com', 'code': code, 'new_password': 'Another-pass-42', 'confirm_password': 'Another-pass-42'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)

    def test_archiving_an_account_signs_it_out_at_once(self):
        device, _login = self.sign_in()
        archive_account(self.admin, self.teacher, 'Left the school')
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)

    def test_an_account_that_cannot_sign_in_is_refused_even_with_an_open_session(self):
        device, _login = self.sign_in()
        User.objects.filter(pk=self.teacher.pk).update(account_status=User.AccountStatus.SUSPENDED)
        response = device.get('/api/auth/me/')
        self.assertEqual((response.status_code, response.data['code']), (401, 'account_unavailable'))
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 401)

    def test_the_admin_can_sign_someone_out_everywhere(self):
        device, _login = self.sign_in()
        admin = APIClient()
        admin.force_authenticate(self.admin)
        response = admin.post(f'/api/admin/accounts/{self.teacher.pk}/sign-out/')
        self.assertEqual((response.status_code, response.data['sign_ins_ended']), (200, 1))
        self.assertEqual(device.get('/api/auth/me/').status_code, 401)
        self.assertTrue(AuditLog.objects.filter(action='sessions_ended_by_admin', target_id=str(self.teacher.pk)).exists())

    def test_old_sessions_are_purged_by_the_daily_job(self):
        self.sign_in()
        AuthSession.objects.update(ended_at=timezone.now() - timedelta(days=40), expires_at=timezone.now() - timedelta(days=40))
        call_command('daily_maintenance', stdout=StringIO())
        self.assertFalse(AuthSession.objects.exists())
        self.assertFalse(SessionToken.objects.exists())


@override_settings(CSRF_TRUSTED_ORIGINS=['https://portal.example'], ALLOWED_HOSTS=['testserver', 'api.example'])
class CsrfTests(SessionFixture):
    def strict(self):
        return APIClient(enforce_csrf_checks=True)

    def csrf(self, client):
        return client.get('/api/auth/csrf/').data['csrf_token']

    def test_sign_in_needs_the_csrf_token(self):
        client = self.strict()
        body = {'identifier': 't@x.com', 'password': PASSWORD}
        missing = client.post('/api/auth/login/', body, format='json')
        self.assertEqual((missing.status_code, missing.data['code']), (403, 'csrf_failed'))
        token = self.csrf(client)
        wrong = client.post('/api/auth/login/', body, format='json', HTTP_X_CSRFTOKEN='x' * 64)
        self.assertEqual(wrong.status_code, 403)
        right = client.post('/api/auth/login/', body, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(right.status_code, 200)

    def test_refresh_and_logout_need_the_csrf_token(self):
        client = self.strict()
        token = self.csrf(client)
        client.post('/api/auth/login/', {'identifier': 't@x.com', 'password': PASSWORD}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(client.post('/api/auth/refresh/').status_code, 403)
        self.assertEqual(client.post('/api/auth/logout/').status_code, 403)
        self.assertEqual(client.post('/api/auth/refresh/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.post('/api/auth/logout/', HTTP_X_CSRFTOKEN=token).status_code, 204)

    def test_a_request_from_another_site_is_refused_even_with_a_token(self):
        client = APIClient(enforce_csrf_checks=True, HTTP_HOST='api.example')
        token = client.get('/api/auth/csrf/', secure=True).data['csrf_token']
        response = client.post(
            '/api/auth/login/',
            {'identifier': 't@x.com', 'password': PASSWORD},
            format='json',
            secure=True,
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN='https://evil.example',
            HTTP_REFERER='https://evil.example/page',
        )
        self.assertEqual(response.status_code, 403)
        allowed = client.post(
            '/api/auth/login/',
            {'identifier': 't@x.com', 'password': PASSWORD},
            format='json',
            secure=True,
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN='https://portal.example',
            HTTP_REFERER='https://portal.example/login',
        )
        self.assertEqual(allowed.status_code, 200)


class StudentSessionTests(SessionFixture):
    def test_a_student_signs_in_with_the_lrn_and_gets_the_same_protections(self):
        student = make_user('s@x.com', User.Role.STUDENT)
        StudentProfile.objects.create(user=student, lrn='136000000009')
        device = APIClient()
        response = device.post('/api/auth/login/', {'identifier': '136000000009', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies[COOKIE]['httponly'])
        self.assertEqual(device.post('/api/auth/refresh/').status_code, 200)
