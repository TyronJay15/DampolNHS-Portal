"""Security regression tests: authentication, access control, input, abuse limits and mail transport."""

from datetime import timedelta
from io import StringIO
from unittest import mock
from urllib.error import HTTPError

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts import mail as portal_mail
from apps.accounts.codes import issue_code
from apps.accounts.models import StudentProfile, User
from apps.cms.tests import TINY_PNG
from apps.notifications.models import Notification
from apps.people.models import TeacherAssignment
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear, Section, Subject

PASSWORD = 'Strongpass1!'


def client_for(user=None, ip='10.0.0.1'):
    client = APIClient(REMOTE_ADDR=ip)
    if user is not None:
        client.force_authenticate(user=user)
    return client


class SecurityFixture(TestCase):
    def setUp(self):
        cache.clear()  # request-limit counters live in the cache
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.programs = make_programs()
        self.admin = User.objects.create_user(email='admin@x.com', password=PASSWORD, role=User.Role.ADMIN)
        self.teacher = self.staff('t1@x.com', User.Role.TEACHER)
        self.other_teacher = self.staff('t2@x.com', User.Role.TEACHER)
        self.student_a = self.student('a@x.com', '136000000001')
        self.student_b = self.student('b@x.com', '136000000002')

    def staff(self, email, role):
        return User.objects.create_user(
            email=email,
            password=PASSWORD,
            role=role,
            approval_status=User.ApprovalStatus.APPROVED,
            account_status=User.AccountStatus.ACTIVE,
        )

    def student(self, email, lrn):
        user = self.staff(email, User.Role.STUDENT)
        return StudentProfile.objects.create(user=user, lrn=lrn)

    def login(self, identifier, password, ip='10.0.0.1'):
        return client_for(ip=ip).post('/api/auth/login/', {'identifier': identifier, 'password': password}, format='json')


class AuthenticationTests(SecurityFixture):
    def test_login_does_not_reveal_which_accounts_exist(self):
        pending = User.objects.create_user(email='new@x.com', password=None, role=User.Role.TEACHER)
        pending.account_status = User.AccountStatus.PENDING_ACTIVATION
        pending.save(update_fields=['account_status'])
        answers = [
            self.login('nobody@x.com', 'whatever'),
            self.login('new@x.com', 'whatever'),
            self.login('t1@x.com', 'wrong-password'),
        ]
        self.assertEqual({(row.status_code, row.data['detail']) for row in answers}, {(401, 'Invalid credentials.')})

    def test_an_archived_account_cannot_sign_in(self):
        self.teacher.account_status = User.AccountStatus.ARCHIVED
        self.teacher.save(update_fields=['account_status'])
        response = self.login('t1@x.com', PASSWORD)
        self.assertEqual((response.status_code, response.data['code']), (401, 'account_deactivated'))

    def test_expired_and_forged_tokens_are_refused(self):
        expired = AccessToken.for_user(self.teacher)
        expired.set_exp(lifetime=-timedelta(seconds=1))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {expired}')
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Bearer not-a-token')
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)
        self.assertEqual(APIClient().post('/api/auth/refresh/').status_code, 401)

    def test_password_reset_and_activation_give_one_answer_for_any_email(self):
        known = client_for().post('/api/auth/forgot-password/otp/', {'identifier': 't1@x.com'}, format='json')
        unknown = client_for().post('/api/auth/forgot-password/otp/', {'identifier': 'nobody@x.com'}, format='json')
        self.assertEqual((known.status_code, known.data), (unknown.status_code, unknown.data))
        payload = {'code': '000000', 'password': PASSWORD, 'confirm_password': PASSWORD}
        active = client_for().post('/api/auth/activate/', {**payload, 'email': 't1@x.com'}, format='json')
        missing = client_for().post('/api/auth/activate/', {**payload, 'email': 'nobody@x.com'}, format='json')
        self.assertEqual((active.status_code, active.data), (missing.status_code, missing.data))

    def test_a_reset_code_cannot_be_guessed_forever(self):
        code = issue_code(self.teacher, 'password', minutes=10)
        wrong = '000000' if code != '000000' else '111111'
        for _attempt in range(5):
            client_for().post('/api/auth/forgot-password/verify/', {'identifier': 't1@x.com', 'code': wrong}, format='json')
        right = client_for().post('/api/auth/forgot-password/verify/', {'identifier': 't1@x.com', 'code': code}, format='json')
        self.assertEqual(right.status_code, 400)  # five wrong guesses cancelled the code, even the right one fails now


class AuthorizationTests(SecurityFixture):
    def test_a_student_only_ever_prints_their_own_grades(self):
        response = client_for(self.student_a.user).get(f'/api/grades/print/?student={self.student_b.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['student']['lrn'], self.student_a.lrn)

    def test_a_student_cannot_reach_staff_or_admin_endpoints(self):
        client = client_for(self.student_a.user)
        for url in (
            '/api/admin/registrations/',
            '/api/admin/staff/',
            '/api/admin/forecast/',
            '/api/audit-logs/',
            '/api/grades/class/',
            '/api/grades/queues/',
            '/api/access/overview/',
            '/api/subjects/',
            '/api/ml/assistant/',
        ):
            self.assertEqual(client.get(url).status_code, 403, url)

    def test_a_teacher_cannot_encode_for_another_teachers_class(self):
        section = Section.objects.create(school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC'])
        subject = Subject.objects.create(code='gen-math', name='General Mathematics')
        theirs = TeacherAssignment.objects.create(
            teacher=self.other_teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            status=TeacherAssignment.Status.ACTIVE,
            school_year=self.year,
            section=section,
            subject=subject,
        )
        response = client_for(self.teacher).post(
            '/api/grades/encode/',
            {'assignment': theirs.pk, 'term': 1, 'student': self.student_a.pk, 'score': 99},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_only_the_head_teacher_approves_grades(self):
        for user in (self.teacher, self.student_a.user, self.admin):
            response = client_for(user).post('/api/grades/approve/all/', {'term': 1}, format='json')
            self.assertEqual(response.status_code, 403, user.role)

    def test_nobody_can_mark_someone_elses_notification(self):
        theirs = Notification.objects.create(user=self.student_b.user, title='x', body='y')
        response = client_for(self.student_a.user).post(f'/api/notifications/{theirs.pk}/read/')
        self.assertEqual(response.status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)


class InputTests(SecurityFixture):
    def test_registration_cannot_choose_a_role_or_approval(self):
        payload = {
            'first_name': 'Eve', 'last_name': 'Cruz', 'lrn': '136000000099', 'email': 'eve@x.com',
            'password': PASSWORD, 'confirm_password': PASSWORD, 'contact_number': '09171234567',
            'address': 'Dampol 1st, Pulilan, Bulacan', 'grade_level_enrollment': 'Grade 11', 'program': 'STEMC',
            'gender': 'female', 'recaptcha_token': '',
            'role': 'admin', 'approval_status': 'approved', 'is_staff': True, 'is_superuser': True,
        }
        self.assertEqual(client_for().post('/api/register/', payload, format='json').status_code, 201)
        eve = User.objects.get(email='eve@x.com')
        self.assertEqual((eve.role, eve.approval_status, eve.is_staff, eve.is_superuser), ('student', 'pending', False, False))

    def test_a_student_cannot_change_protected_profile_fields(self):
        client = client_for(self.student_a.user)
        client.patch(
            '/api/students/me/',
            {'contact_number': '09179876543', 'address': 'Dampol 1st, Pulilan', 'gender': 'female', 'lrn': '999', 'role': 'admin'},
            format='json',
        )
        self.student_a.refresh_from_db()
        self.student_a.user.refresh_from_db()
        self.assertEqual((self.student_a.lrn, self.student_a.user.role), ('136000000001', 'student'))

    def test_a_renamed_file_is_not_accepted_as_a_photo(self):
        client = client_for(self.admin)
        fake = SimpleUploadedFile('photo.png', b'<script>alert(1)</script>', content_type='image/png')
        self.assertEqual(client.post('/api/cms/media/', {'file': fake}, format='multipart').status_code, 400)
        real = SimpleUploadedFile('photo.png', TINY_PNG, content_type='image/png')
        created = client.post('/api/cms/media/', {'file': real}, format='multipart')
        self.assertEqual(created.status_code, 201)
        client.delete('/api/cms/media/', {'url': created.data['url']}, format='json')

    def test_an_oversized_chatbot_question_is_refused(self):
        response = client_for().post('/api/chatbot/', {'question': 'x' * 401}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_malformed_ids_are_refused(self):
        client = client_for(self.admin)
        self.assertEqual(client.post('/api/admin/registrations/approve-bulk/', {'ids': 'all'}, format='json').status_code, 400)
        self.assertEqual(client.post('/api/admin/registrations/999999/approve/').status_code, 404)


LIMITS = {'login': '3/min', 'login_account': '2/hour', 'codes': '2/hour', 'chatbot': '2/min', 'retrain': '1/hour'}


@override_settings(API_THROTTLE_RATES=LIMITS)
class AbuseLimitTests(SecurityFixture):
    def test_repeated_logins_are_limited_per_visitor(self):
        answers = [self.login(f'x{index}@x.com', 'nope').status_code for index in range(4)]
        self.assertEqual(answers, [401, 401, 401, 429])

    def test_one_account_is_limited_even_from_many_addresses(self):
        answers = [self.login('t1@x.com', 'nope', ip=f'10.0.1.{index}').status_code for index in range(3)]
        self.assertEqual(answers, [401, 401, 429])

    def test_repeated_password_reset_requests_are_limited(self):
        client = client_for()
        answers = [client.post('/api/auth/forgot-password/otp/', {'identifier': 't1@x.com'}, format='json').status_code for _ in range(3)]
        self.assertEqual(answers, [200, 200, 429])

    def test_the_chatbot_is_limited(self):
        client = client_for()
        answers = [client.post('/api/chatbot/', {'question': 'How do I enroll?'}, format='json').status_code for _ in range(3)]
        self.assertEqual(answers[-1], 429)

    def test_retraining_is_limited_but_reading_the_page_is_not(self):
        client = client_for(self.admin)
        self.assertEqual([client.post('/api/admin/forecast/').status_code for _ in range(2)], [200, 429])
        self.assertEqual([client.get('/api/admin/forecast/').status_code for _ in range(3)], [200, 200, 200])


@override_settings(DEBUG=False, TESTING=False)
class FirstAdminTests(TestCase):
    def test_production_refuses_the_default_or_a_weak_admin_password(self):
        for password in ('changeme123', 'short'):
            with self.assertRaises(CommandError):
                call_command('setup_school', password=password, stdout=StringIO())
        self.assertFalse(User.objects.filter(email='admin@dampol1nhs.edu.ph').exists())
        call_command('setup_school', password='A-long-Strong-passphrase-2026', stdout=StringIO())
        self.assertTrue(User.objects.get(email='admin@dampol1nhs.edu.ph').check_password('A-long-Strong-passphrase-2026'))


@override_settings(MAIL_TRANSPORT='brevo_api', BREVO_API_KEY='test-key', DEFAULT_FROM_EMAIL='noreply@x.com')
class BrevoTransportTests(TestCase):
    def test_the_key_goes_in_a_header_and_the_recipient_is_fixed(self):
        with mock.patch.object(portal_mail, 'urlopen') as opened:
            opened.return_value.__enter__.return_value.read.return_value = b'{}'
            portal_mail.send_message('student@x.com', 'Subject', 'Body')
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, portal_mail.BREVO_URL)
        self.assertEqual(request.get_header('Api-key'), 'test-key')
        self.assertNotIn('test-key', request.full_url)
        self.assertIn(b'"student@x.com"', request.data)

    def test_a_bad_address_is_final_and_an_outage_is_retried(self):
        for code, permanent in ((400, True), (503, False)):
            error = HTTPError(portal_mail.BREVO_URL, code, 'error', {}, None)
            with mock.patch.object(portal_mail, 'urlopen', side_effect=error):
                with self.assertRaises(portal_mail.MailError) as raised:
                    portal_mail.send_message('student@x.com', 'Subject', 'Body')
            self.assertEqual(raised.exception.permanent, permanent)
            self.assertNotIn('test-key', str(raised.exception))
