"""Security plan Phase 1 and 2 regression tests: passwords (W4), registration privacy (W12), chatbot privacy (W12),
link checks (W13), bad ids (N1), failed sign-in limits and alerts (W9), log privacy (W16)."""

from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import mail as portal_mail
from apps.accounts.models import MailOutbox, StudentProfile, User
from apps.audit.models import AuditLog
from apps.cms.links import is_safe_link, unsafe_links
from apps.ml.models import ChatQuestion
from apps.notifications.models import Notification
from apps.people.models import Registration
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear

PASSWORD = 'Strongpass1!'
REGISTRATION = {
    'first_name': 'Ana', 'last_name': 'Reyes', 'lrn': '136000000001', 'email': 'ana@x.com',
    'password': 'Blue-river-2026', 'confirm_password': 'Blue-river-2026', 'contact_number': '09171234567',
    'address': 'Dampol 1st, Pulilan, Bulacan', 'gender': 'female', 'recaptcha_token': '',
    'grade_level_enrollment': 'Grade 11', 'program': 'STEMC',
}


def make_user(email, role=User.Role.TEACHER):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name='Juan',
        last_name='Delacruz',
        role=role,
        approval_status=User.ApprovalStatus.APPROVED,
        account_status=User.AccountStatus.ACTIVE,
    )


class PasswordRuleTests(TestCase):
    def setUp(self):
        SchoolYear.objects.create(label='2026-2027', is_current=True)
        make_programs()

    def register(self, password, **extra):
        body = {**REGISTRATION, 'password': password, 'confirm_password': password, **extra}
        return APIClient().post('/api/register/', body, format='json')

    def test_students_need_ten_characters_a_letter_and_a_number(self):
        for weak in ('short1a', 'onlyletterspass', '1234567890123'):
            response = self.register(weak)
            self.assertEqual(response.status_code, 400, weak)
            self.assertIn('password', response.data['errors'])
        self.assertEqual(self.register('Blue-river-2026').status_code, 201)

    def test_common_and_personal_passwords_are_refused(self):
        self.assertEqual(self.register('password123').status_code, 400)
        self.assertEqual(self.register('anareyes2026', email='anareyes2026@x.com').status_code, 400)

    def test_staff_need_twelve_characters(self):
        from apps.accounts.passwords import check_new_password
        from rest_framework.exceptions import ValidationError

        staff = User(email='t@x.com', first_name='T', last_name='C', role=User.Role.TEACHER)
        with self.assertRaises(ValidationError):
            check_new_password('Gr8-teacher', staff)  # 11 characters
        self.assertEqual(check_new_password('Gr8-teacher!', staff), 'Gr8-teacher!')


@override_settings(MAIL_DELIVERY='background')
class RegistrationPrivacyTests(TestCase):
    def setUp(self):
        SchoolYear.objects.create(label='2026-2027', is_current=True)
        make_programs()
        self.owner = make_user('ana@x.com', User.Role.STUDENT)
        StudentProfile.objects.create(user=self.owner, lrn='136000000001')

    def register(self, **extra):
        return APIClient().post('/api/register/', {**REGISTRATION, **extra}, format='json')

    def test_new_and_existing_details_get_the_same_answer(self):
        repeat_email = self.register(lrn='136000000050')
        repeat_lrn = self.register(email='new-person@x.com')
        new = self.register(email='fresh@x.com', lrn='136000000077')
        answers = {(row.status_code, row.data['detail'], row.data['approval_status']) for row in (repeat_email, repeat_lrn, new)}
        self.assertEqual(len(answers), 1, answers)

    def test_a_repeat_creates_nothing_and_tells_the_real_owner_once(self):
        before = User.objects.count()
        self.register(lrn='136000000050')
        self.register(lrn='136000000051')
        self.assertEqual(User.objects.count(), before)
        notices = MailOutbox.objects.filter(user=self.owner, subject=portal_mail.DUPLICATE_NOTICE_SUBJECT)
        self.assertEqual(notices.count(), 1)  # the second repeat inside six hours sends nothing more
        self.assertEqual(notices.get().status, MailOutbox.Status.QUEUED)  # sent later by the sender, not in the request
        self.assertEqual(AuditLog.objects.filter(action='register_duplicate').count(), 2)

    def test_a_new_registration_still_works(self):
        response = self.register(email='fresh@x.com', lrn='136000000077')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Registration.objects.filter(user__email='fresh@x.com').exists())


class ChatbotPrivacyTests(TestCase):
    def ask(self, question):
        return APIClient().post('/api/chatbot/', {'question': question}, format='json')

    def test_personal_details_are_removed_before_saving_and_before_gemini(self):
        with mock.patch('apps.chatbot.views.phrase_answer', return_value=None) as gemini, mock.patch(
            'apps.chatbot.views.classify_question', return_value=('enrollment', 0.9)
        ), mock.patch('apps.chatbot.views.answers_for', return_value=['Visit the office.']):
            self.ask('My LRN is 1360-0000-0123 and my email ana.reyes@gmail.com, call 0917 123 4567. Enrollment?')
        stored = ChatQuestion.objects.get().question
        for secret in ('1360-0000-0123', '136000000123', 'ana.reyes@gmail.com', '0917 123 4567'):
            self.assertNotIn(secret, stored)
            self.assertNotIn(secret, gemini.call_args.args[0])
        self.assertIn('[email removed]', stored)
        self.assertIn('[number removed]', stored)

    def test_short_numbers_like_years_and_grades_stay(self):
        with mock.patch('apps.chatbot.views.phrase_answer', return_value=None):
            self.ask('Is enrollment for Grade 11 open in 2026?')
        self.assertIn('2026', ChatQuestion.objects.get().question)

    def test_old_question_text_is_blanked_but_the_statistics_stay(self):
        old = ChatQuestion.objects.create(question='When is enrollment?', topic='enrollment', source='faq')
        ChatQuestion.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=91))
        recent = ChatQuestion.objects.create(question='Where is the school?', topic='location', source='faq')
        call_command('daily_maintenance', stdout=StringIO())
        old.refresh_from_db()
        recent.refresh_from_db()
        self.assertEqual((old.question, old.topic, old.source), ('', 'enrollment', 'faq'))
        self.assertEqual(recent.question, 'Where is the school?')


class LinkCheckTests(TestCase):
    def test_only_site_paths_and_allowed_schemes_pass(self):
        for good in ('/about', '#top', 'https://deped.gov.ph', 'http://x.ph', 'mailto:office@x.ph', 'tel:+63441234567', ''):
            self.assertTrue(is_safe_link(good), good)
        for bad in ('javascript:alert(1)', 'JavaScript:alert(1)', ' java\tscript:alert(1)', 'data:text/html,x', 'vbscript:x'):
            self.assertFalse(is_safe_link(bad), bad)

    def test_unsafe_links_are_found_anywhere_in_a_page(self):
        page = {'title': 'Note: hello', 'links': [{'label': 'Home', 'to': '/'}, {'label': 'x', 'to': 'javascript:alert(1)'}],
                'facebook_url': 'https://facebook.com/x'}
        self.assertEqual(unsafe_links(page), ['links[1].to'])

    def test_the_cms_refuses_a_javascript_link(self):
        admin = make_user('admin@x.com', User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(admin)
        body = {'document': 'footer', 'payload': {'facebook_url': 'javascript:alert(1)'}}
        response = client.patch('/api/cms/content/', body, format='json')
        self.assertEqual(response.status_code, 400)


class BadIdTests(TestCase):
    def test_a_non_numeric_id_is_a_clean_400_not_a_server_error(self):
        head = make_user('head@x.com', User.Role.HEAD_TEACHER)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(head)
        response = client.get('/api/grades/queues/?term=abc')
        self.assertEqual((response.status_code, response.data['code']), (400, 'invalid_id'))


@override_settings(API_THROTTLE_RATES={'login_account': '3/hour'})
class FailedSignInTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user('admin@x.com', User.Role.ADMIN)
        self.teacher = make_user('t@x.com')

    def login(self, password, ip='10.0.0.1'):
        return APIClient(REMOTE_ADDR=ip).post('/api/auth/login/', {'identifier': 't@x.com', 'password': password}, format='json')

    def test_only_failures_count_towards_the_account_limit(self):
        for _ in range(5):
            self.assertEqual(self.login(PASSWORD).status_code, 200)

    def test_repeated_failures_pause_the_account_and_alert_the_admin_once(self):
        for attempt in range(3):
            self.assertEqual(self.login('wrong', ip=f'10.0.0.{attempt}').status_code, 401)
        self.assertEqual(self.login(PASSWORD, ip='10.0.0.9').status_code, 429)
        self.assertEqual(AuditLog.objects.filter(action='login_locked').count(), 1)
        alerts = Notification.objects.filter(user=self.admin, category='security', title__startswith='Sign-in paused')
        self.assertEqual(alerts.count(), 1)
        self.assertNotIn('t@x.com', alerts.get().body)  # accounts are named by number only


class LogPrivacyTests(TestCase):
    def test_mail_log_lines_mask_the_address(self):
        self.assertEqual(portal_mail.masked('ana.reyes@gmail.com'), 'a***@gmail.com')
        self.assertEqual(portal_mail.masked('not-an-email'), '***')


class HealthReadyTests(TestCase):
    def test_liveness_does_not_need_the_database_shape(self):
        response = APIClient().get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'service': 'dampol-nhs-portal'})

    def test_ready_confirms_mysql(self):
        response = APIClient().get('/api/health/ready/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ready'})

    def test_ready_is_not_ready_when_mysql_fails(self):
        with mock.patch('apps.accounts.views_health.connection') as db:
            db.cursor.return_value.__enter__.return_value.execute.side_effect = RuntimeError('database down')
            response = APIClient().get('/api/health/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'not_ready'})
        self.assertNotIn('database down', response.content.decode())

