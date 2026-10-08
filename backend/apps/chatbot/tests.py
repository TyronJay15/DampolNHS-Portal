"""Chatbot live data: today's enrollment total from the database, answered to any visitor of the public chatbot."""

from unittest import mock

from django.core.cache import cache
from django.db import DatabaseError
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.chatbot.live_data import LIVE_TOPICS, NO_SCHOOL_YEAR, LiveTopic, current_enrollment_summary, live_answer
from apps.chatbot.seeds import seed_faqs
from apps.ml.intent import classify_question, train_intent
from apps.ml.models import ChatQuestion
from apps.people.models import Registration, StudentSection
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear, Section

QUESTION = 'How many students are currently enrolled?'


def make_user(email, role, status=User.AccountStatus.ACTIVE):
    return User.objects.create_user(
        email=email, password='Strongpass1!', role=role,
        approval_status=User.ApprovalStatus.APPROVED, account_status=status,
    )


class LiveDataFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_faqs()
        train_intent()

    def setUp(self):
        cache.clear()
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.last_year = SchoolYear.objects.create(label='2025-2026', is_current=False)
        self.programs = make_programs()
        self.count = 0
        self.grade11 = Section.objects.create(
            school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC']
        )
        self.grade12 = Section.objects.create(
            school_year=self.year, name='STEM-A', grade_level='Grade 12', program=self.programs['STEM']
        )
        self.old_section = Section.objects.create(
            school_year=self.last_year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC']
        )

    def register(self, year=None, status=Registration.Status.APPROVED, account=User.AccountStatus.ACTIVE):
        self.count += 1
        user = make_user(f'student{self.count}@x.com', User.Role.STUDENT, account)
        return Registration.objects.create(
            user=user, school_year=year or self.year, program=self.programs['STEMC'],
            grade_level_enrollment='Grade 11', status=status,
        )

    def place(self, registration, section=None, active=True):
        """Put the registration's student in a section (this year's Grade 11 section by default)."""
        section = section or self.grade11
        profile, _created = StudentProfile.objects.get_or_create(
            user=registration.user, defaults={'lrn': f'1360000{registration.user_id:05d}'}
        )
        return StudentSection.objects.create(
            student=profile, section=section, school_year=section.school_year, is_active=active
        )

    def returning_grade12(self, account=User.AccountStatus.ACTIVE):
        """A student who registered last year and is placed in Grade 12 this year, with no new registration."""
        return self.place(self.register(year=self.last_year, account=account), self.grade12)

    def ask(self, user=None, question=QUESTION):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client.post('/api/chatbot/', {'question': question}, format='json')


class IntentTests(LiveDataFixture):
    def test_enrollment_questions_reach_the_live_topic(self):
        for question in (
            QUESTION,
            'How many students are enrolled?',
            'total enrolled students this school year',
            'ilan ang enrolled students ngayon?',
            'number of enrolled students',
            'What is the current student population?',
            'Ilang estudyante ang kasalukuyang enrolled?',
        ):
            self.assertEqual(classify_question(question)[0], 'enrollment_stats', question)

    def test_how_to_enroll_still_means_registration(self):
        for question in ('How do I register?', 'paano mag enroll', 'where do i enroll'):
            self.assertEqual(classify_question(question)[0], 'registration', question)


class CountTests(LiveDataFixture):
    def test_returning_grade12_students_are_counted(self):
        self.returning_grade12()
        self.returning_grade12()
        summary = current_enrollment_summary()
        self.assertEqual(summary['total'], 2)
        self.assertEqual((summary['registered_this_year'], summary['placed_in_sections']), (0, 2))

    def test_the_current_student_body_counts_each_student_once(self):
        self.place(self.register())  # approved this year and already placed: once, not twice
        self.register()  # approved this year, not placed yet
        self.returning_grade12()  # placed this year, registration from last year
        summary = current_enrollment_summary()
        self.assertEqual(
            summary,
            {
                'available': True,
                'school_year': '2026-2027',
                'total': 3,
                'registered_this_year': 2,
                'placed_in_sections': 2,
            },
        )

    def test_pending_rejected_and_earlier_years_do_not_count(self):
        self.register()
        self.register(status=Registration.Status.PENDING)
        self.register(status=Registration.Status.REJECTED)
        self.register(year=self.last_year)  # last year, not placed this year: graduated or left
        self.place(self.register(year=self.last_year), self.old_section)  # placed only last year
        self.assertEqual(current_enrollment_summary()['total'], 1)

    def test_an_ended_placement_does_not_count(self):
        self.place(self.register(year=self.last_year), self.grade12, active=False)
        self.assertEqual(current_enrollment_summary()['total'], 0)

    def test_archived_removed_and_suspended_accounts_do_not_count(self):
        self.register()
        for status in (User.AccountStatus.ARCHIVED, User.AccountStatus.REMOVED, User.AccountStatus.SUSPENDED):
            self.register(account=status)
            self.returning_grade12(account=status)
        self.assertEqual(current_enrollment_summary()['total'], 1)

    def test_no_current_school_year_is_not_a_zero(self):
        SchoolYear.objects.update(is_current=False)
        self.assertEqual(current_enrollment_summary(), {'available': False, 'message': NO_SCHOOL_YEAR})

    def test_an_archived_current_year_is_not_used(self):
        SchoolYear.objects.filter(pk=self.year.pk).update(archived_at=timezone.now())
        self.assertFalse(current_enrollment_summary()['available'])

    def test_counting_changes_nothing(self):
        self.place(self.register())
        self.returning_grade12()
        before = (Registration.objects.count(), StudentSection.objects.count(), User.objects.count())
        with self.assertNumQueries(4):  # the current year, then three COUNT queries; no rows are loaded
            current_enrollment_summary()
        self.assertEqual((Registration.objects.count(), StudentSection.objects.count(), User.objects.count()), before)


class ChatbotAccessTests(LiveDataFixture):
    def test_every_visitor_and_role_gets_the_same_live_total(self):
        self.register()  # approved, not placed yet
        self.returning_grade12()  # registered last year, placed this year
        self.place(self.register())  # approved and placed: counts once
        askers = [None] + [make_user(f'{role}@x.com', role) for role in User.Role.values]
        for user in askers:
            response = self.ask(user)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['answer'], 'There are currently 3 enrolled students for School Year 2026-2027.')
            self.assertEqual(response.data['topic'], 'enrollment_stats')

    def test_the_answer_follows_the_database_without_retraining(self):
        self.register()
        self.assertIn(' 1 enrolled student ', self.ask().data['answer'])
        self.returning_grade12()
        self.assertIn(' 2 enrolled students ', self.ask().data['answer'])

    def test_zero_is_reported_as_zero(self):
        self.assertEqual(self.ask().data['answer'], 'There are currently 0 enrolled students for School Year 2026-2027.')

    def test_no_school_year_gives_a_safe_message(self):
        SchoolYear.objects.update(is_current=False)
        response = self.ask()
        self.assertEqual((response.status_code, response.data['answer']), (200, NO_SCHOOL_YEAR))

    def test_only_the_total_and_school_year_are_returned(self):
        registration = self.register()
        User.objects.filter(pk=registration.user_id).update(first_name='Ana', last_name='Reyes')
        placement = self.place(registration)
        response = self.ask()
        self.assertEqual(set(response.data), {'answer', 'topic', 'confidence', 'kind', 'options'})
        self.assertEqual(response.data['options'], [])
        answer = response.data['answer']
        for private in ('Ana', 'Reyes', registration.user.email, placement.student.lrn, self.grade11.name, 'approved'):
            self.assertNotIn(private, answer)

    def test_gemini_never_sees_a_live_question(self):
        with mock.patch('apps.chatbot.assistant.phrase_answer') as gemini:
            self.ask()
        gemini.assert_not_called()

    def test_a_database_failure_gives_no_number_and_no_server_error(self):
        with mock.patch('apps.chatbot.live_data.Registration.objects.filter', side_effect=DatabaseError('boom')):
            response = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('boom', response.data['answer'])
        self.assertEqual(ChatQuestion.objects.get().source, 'live_error')

    def test_the_log_keeps_the_redacted_question_and_the_source_only(self):
        self.register()
        self.ask(question=f'{QUESTION} email me at ana@gmail.com')
        row = ChatQuestion.objects.get()
        self.assertEqual((row.topic, row.source), ('enrollment_stats', 'live_data'))
        self.assertNotIn('ana@gmail.com', row.question)
        self.assertIn('[email removed]', row.question)


class ProtectedTopicTests(TestCase):
    """Making enrollment public did not make every live topic public: a role-limited topic is still checked on the
    server against the signed-in account."""

    def setUp(self):
        topic = LiveTopic(
            roles=frozenset({User.Role.ADMIN}),
            summary=lambda: {'secret': 42},
            sentence=lambda data: f'The figure is {data["secret"]}.',
            refused='Only administrators can see that.',
        )
        patcher = mock.patch.dict(LIVE_TOPICS, {'staff_only': topic})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_the_listed_roles_receive_the_answer(self):
        self.assertEqual(live_answer('staff_only', make_user('admin@x.com', User.Role.ADMIN)), ('The figure is 42.', 'live_data'))
        for user in (AnonymousUser(), make_user('t@x.com', User.Role.TEACHER), make_user('s@x.com', User.Role.STUDENT)):
            answer, source = live_answer('staff_only', user)
            self.assertEqual((answer, source), ('Only administrators can see that.', 'live_denied'))
            self.assertNotIn('42', answer)

    def test_an_account_that_cannot_sign_in_is_refused(self):
        admin = make_user('admin@x.com', User.Role.ADMIN, User.AccountStatus.ARCHIVED)
        self.assertEqual(live_answer('staff_only', admin)[1], 'live_denied')


class PublicChatbotTests(LiveDataFixture):
    def test_visitors_still_get_normal_answers(self):
        with mock.patch('apps.chatbot.assistant.phrase_answer', return_value=None):
            response = APIClient().post('/api/chatbot/', {'question': 'How do I register?'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['topic'], 'registration')
        self.assertIn('Register', response.data['answer'])
