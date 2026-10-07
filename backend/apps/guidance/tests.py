"""Student flows: consent, the assessment, saved recommendations, browsing and object-level access."""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.grading.models import Grade
from apps.guidance.catalog import activate_instrument
from apps.guidance.consent import NOTICE_VERSION
from apps.guidance.models import (
    GuidanceConsent,
    InterestAssessment,
    InterestInstrument,
    InterestQuestion,
    InterestResponse,
    RecommendationRun,
)
from apps.guidance.testing import GuidanceFixture
from apps.ml.models import CollegeProgram


class ConsentTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student()
        self.client = self.client_for(self.student.user)

    def give(self, kind='assessment', **extra):
        return self.client.post(
            '/api/guidance/me/consent/',
            {'kind': kind, 'notice_version': NOTICE_VERSION, **extra},
            format='json',
        )

    def test_overview_shows_the_notice_and_no_consent_yet(self):
        data = self.client.get('/api/guidance/me/').data
        self.assertIsNone(data['consent']['assessment'])
        self.assertEqual(data['consent']['notice']['version'], NOTICE_VERSION)
        titles = [section['title'] for section in data['consent']['notice']['sections']]
        self.assertNotIn('Helping improve the recommender (optional)', titles)
        body = ' '.join(section['body'] for section in data['consent']['notice']['sections'])
        self.assertIn('ML recommendation', body)
        self.assertNotIn('train the recommender', body.lower())

    def test_adult_gives_consent_and_it_is_audited(self):
        response = self.give()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['consent']['assessment']['party'], GuidanceConsent.Party.STUDENT)
        self.assertTrue(AuditLog.objects.filter(action='guidance_consent_given').exists())

    def test_minor_needs_a_guardian_confirmation(self):
        minor = self.make_student(adult=False)
        client = self.client_for(minor.user)
        refused = client.post('/api/guidance/me/consent/', {'kind': 'assessment', 'notice_version': NOTICE_VERSION}, format='json')
        self.assertEqual(refused.status_code, 400)
        accepted = client.post(
            '/api/guidance/me/consent/',
            {'kind': 'assessment', 'notice_version': NOTICE_VERSION, 'guardian_confirmed': True},
            format='json',
        )
        self.assertEqual(accepted.data['consent']['assessment']['party'], GuidanceConsent.Party.STUDENT_AND_GUARDIAN)

    def test_an_old_notice_version_is_refused(self):
        response = self.client.post('/api/guidance/me/consent/', {'kind': 'assessment', 'notice_version': '1999-01'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_training_consent_needs_assessment_consent_first(self):
        self.assertEqual(self.give('training').status_code, 400)
        self.give()
        self.assertEqual(self.give('training').status_code, 200)

    def test_withdrawing_deletes_answers_and_saved_recommendations(self):
        self.give()
        self.give('training')
        self.complete_assessment(self.student)
        self.client.get('/api/guidance/me/')
        self.assertTrue(RecommendationRun.objects.filter(student=self.student).exists())
        response = self.client.post('/api/guidance/me/consent/withdraw/', {'kind': 'assessment'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterestAssessment.objects.filter(student=self.student).exists())
        self.assertEqual(
            GuidanceConsent.objects.filter(student=self.student, withdrawn_at__isnull=True).count(),
            0,
        )
        # Consent records stay as proof of what was agreed and withdrawn.
        self.assertEqual(GuidanceConsent.objects.filter(student=self.student).count(), 2)
        # The page still works afterwards; the matcher stays gated until they agree again.
        self.assertFalse(response.data['recommendation']['ready'])
        self.assertEqual(response.data['recommendation']['method_label'], 'ML recommendation')


class AssessmentTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student()
        self.consent(self.student)
        self.client = self.client_for(self.student.user)
        self.questions = list(InterestQuestion.objects.filter(instrument=self.instrument).order_by('position'))

    def answer(self, question, value):
        return self.client.put('/api/guidance/me/assessment/answer/', {'question': question, 'value': value}, format='json')

    def test_the_assessment_has_thirty_questions_without_their_interest_types(self):
        data = self.client.get('/api/guidance/me/assessment/').data
        self.assertEqual(len(data['instrument']['questions']), 30)
        self.assertNotIn('riasec', data['instrument']['questions'][0])
        self.assertIn('USDOL/ETA', data['instrument']['attribution'])
        self.assertNotIn('CC BY-ND', data['instrument']['attribution'])

    def test_students_see_shs_age_questions_not_adult_mini_ip(self):
        from apps.guidance.instrument_seed import DAMPOL_ITEMS, DAMPOL_NAME, ITEMS

        data = self.client.get('/api/guidance/me/assessment/').data
        self.assertEqual(data['instrument']['name'], DAMPOL_NAME)
        self.assertEqual(data['instrument']['version'], 2)
        texts = [row['text'] for row in data['instrument']['questions']]
        self.assertEqual(texts, [text for _position, _letter, text in DAMPOL_ITEMS])
        adult = {text.lower() for _position, _letter, text in ITEMS}
        for text in texts:
            self.assertTrue(text.startswith('Would you enjoy '))
            self.assertNotIn(text.removeprefix('Would you enjoy ').rstrip('?').lower(), adult)

    def test_reseeding_refreshes_shs_wording(self):
        from django.apps import apps
        from apps.guidance.instrument_seed import DAMPOL_ITEMS, seed_dampol_instrument

        stale = InterestQuestion.objects.get(instrument=self.instrument, position=1)
        stale.text = 'Would you enjoy building kitchen cabinets?'
        stale.save(update_fields=['text'])
        seed_dampol_instrument(apps.get_model)
        stale.refresh_from_db()
        self.assertEqual(stale.text, DAMPOL_ITEMS[0][2])

    def test_full_attempt_scores_each_type_as_the_mean_of_its_answers(self):
        self.client.post('/api/guidance/me/assessment/start/')
        for question in self.questions:
            self.assertEqual(self.answer(question.pk, 5 if question.riasec == 'I' else 2).status_code, 200)
        response = self.client.post('/api/guidance/me/assessment/complete/')
        self.assertEqual(response.status_code, 200, response.data)
        attempt = InterestAssessment.objects.get(student=self.student)
        self.assertEqual(attempt.status, InterestAssessment.Status.COMPLETED)
        self.assertEqual(attempt.scores, {'R': 2.0, 'I': 5.0, 'A': 2.0, 'S': 2.0, 'E': 2.0, 'C': 2.0})
        self.assertEqual(attempt.instrument.version, 2)

    def test_answers_are_saved_so_the_student_can_continue_later(self):
        self.client.post('/api/guidance/me/assessment/start/')
        self.answer(self.questions[0].pk, 4)
        self.answer(self.questions[0].pk, 5)
        data = self.client.get('/api/guidance/me/assessment/').data
        self.assertEqual(data['attempt']['answers'], {self.questions[0].pk: 5})
        self.assertEqual(InterestResponse.objects.count(), 1)

    def test_invalid_answers_are_rejected(self):
        self.client.post('/api/guidance/me/assessment/start/')
        for value in (0, 6, '3', True, None, 2.5):
            self.assertEqual(self.answer(self.questions[0].pk, value).status_code, 400, value)
        self.assertEqual(self.answer('abc', 3).status_code, 400)
        self.assertEqual(InterestResponse.objects.count(), 0)

    def test_completing_with_unanswered_questions_is_refused(self):
        self.client.post('/api/guidance/me/assessment/start/')
        self.answer(self.questions[0].pk, 3)
        self.assertEqual(self.client.post('/api/guidance/me/assessment/complete/').status_code, 400)

    def test_no_consent_means_no_assessment(self):
        other = self.make_student()
        self.assertEqual(self.client_for(other.user).post('/api/guidance/me/assessment/start/').status_code, 400)

    def test_a_new_instrument_version_replaces_an_unfinished_attempt(self):
        self.client.post('/api/guidance/me/assessment/start/')
        self.answer(self.questions[0].pk, 3)
        newer = InterestInstrument.objects.create(
            code=self.instrument.code,
            version=self.instrument.version + 1,
            name=self.instrument.name,
            source=self.instrument.source,
            attribution=self.instrument.attribution,
        )
        InterestQuestion.objects.bulk_create(
            [
                InterestQuestion(instrument=newer, position=row.position, text=row.text, original_text=row.text, riasec=row.riasec)
                for row in self.questions
            ]
        )
        activate_instrument(newer, user=self.admin, license_confirmed=True)
        self.client.post('/api/guidance/me/assessment/start/')
        attempt = InterestAssessment.objects.get(student=self.student)
        self.assertEqual(attempt.instrument, newer)
        self.assertEqual(attempt.responses.count(), 0)

    def test_student_can_delete_their_answers(self):
        self.complete_assessment(self.student)
        response = self.client.delete('/api/guidance/me/assessment/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterestAssessment.objects.filter(student=self.student).exists())
        self.assertTrue(AuditLog.objects.filter(action='guidance_data_deleted').exists())


class RecommendationRunTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student('tech')
        self.client = self.client_for(self.student.user)

    def test_profile_matching_works_without_any_model_and_says_so(self):
        self.consent(self.student)
        data = self.client.get('/api/guidance/me/').data['recommendation']
        self.assertTrue(data['ready'])
        self.assertEqual(data['method'], 'profile_matching')
        self.assertEqual(data['method_label'], 'ML recommendation')
        self.assertEqual(len(data['primary']), 3)
        self.assertLessEqual(len(data['primary']) + len(data['additional']), 10)
        run = RecommendationRun.objects.get(student=self.student)
        self.assertEqual(run.method, RecommendationRun.Method.PROFILE_MATCHING)
        self.assertIsNone(run.family_model)
        self.assertIsNotNone(run.config)

    def test_without_consent_the_matcher_is_gated(self):
        data = self.client.get('/api/guidance/me/').data['recommendation']
        self.assertFalse(data['ready'])
        self.assertIn('Agree to college recommendation', data['not_ready'])
        self.assertIsNone(data['id'])
        self.assertFalse(RecommendationRun.objects.filter(student=self.student).exists())

    def test_without_an_assessment_every_item_is_limited_evidence(self):
        self.consent(self.student)
        data = self.client.get('/api/guidance/me/').data['recommendation']
        self.assertTrue(all(item['label'] == 'limited' for item in data['primary'] + data['additional']))

    def test_a_run_is_reused_until_its_inputs_change(self):
        self.consent(self.student)
        self.client.get('/api/guidance/me/')
        self.client.get('/api/guidance/me/')
        self.assertEqual(RecommendationRun.objects.filter(student=self.student).count(), 1)
        self.complete_assessment(self.student)
        self.client.get('/api/guidance/me/')
        self.assertEqual(RecommendationRun.objects.filter(student=self.student).count(), 2)

    def test_only_released_grades_are_used_for_the_student(self):
        self.consent(self.student)
        before = self.client.get('/api/guidance/me/').data['recommendation']['skills']
        Grade.objects.create(
            student=self.student,
            subject=self.subject_for('arts'),
            term=self.term,
            school_year=self.year,
            score=Decimal('99'),
            status=Grade.Status.APPROVED,
        )
        Grade.objects.create(
            student=self.student,
            subject=self.subject_for('service'),
            term=self.term,
            school_year=self.year,
            score=Decimal('99'),
            status=Grade.Status.DRAFT,
        )
        after = self.client.get('/api/guidance/me/').data['recommendation']['skills']
        self.assertEqual(before, after)
        self.assertNotIn('arts', [row['key'] for row in after])

    def test_missing_domains_are_never_reported_as_zero(self):
        self.consent(self.student)
        skills = self.client.get('/api/guidance/me/').data['recommendation']['skills']
        self.assertEqual({row['key'] for row in skills}, {'tech', 'math', 'language', 'social'})
        self.assertTrue(all(row['value'] not in (None, '0', '0.00') for row in skills))

    def test_explanations_use_the_students_real_values(self):
        self.consent(self.student)
        self.complete_assessment(self.student)
        data = self.client.get('/api/guidance/me/').data['recommendation']
        first = data['primary'][0]
        text = ' '.join(first['explanation'])
        for row in first['evidence']['strengths'][:2]:
            self.assertIn(f'{row["label"]} ({row["student"].rstrip("0").rstrip(".")})', text)
        self.assertNotIn('%', text)
        self.assertNotIn('accuracy', text.lower())

    def test_too_few_grades_is_explained_not_failed(self):
        thin = self.make_student('tech')
        self.consent(thin)
        Grade.objects.filter(student=thin).exclude(subject__skill_domain__key='tech').delete()
        data = self.client_for(thin.user).get('/api/guidance/me/').data['recommendation']
        self.assertFalse(data['ready'])
        self.assertIn('three skill areas', data['not_ready'])


class BrowseAndCompareTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student('science')
        self.client = self.client_for(self.student.user)

    def test_the_whole_active_catalog_can_be_browsed(self):
        data = self.client.get('/api/guidance/programs/').data
        self.assertEqual(len(data['programs']), CollegeProgram.objects.filter(is_active=True).count())
        CollegeProgram.objects.filter(code='bsn').update(is_active=False)
        codes = [row['code'] for row in self.client.get('/api/guidance/programs/').data['programs']]
        self.assertNotIn('bsn', codes)

    def test_any_program_shows_how_the_student_relates_to_it(self):
        self.consent(self.student)
        response = self.client.get('/api/guidance/me/programs/bshrm/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data['fit']['status'], ('evaluated', 'not_checked'))
        self.assertEqual(self.client.get('/api/guidance/me/programs/no-such-program/').status_code, 404)

    def test_compare_takes_two_or_three_programs(self):
        self.consent(self.student)
        ok = self.client.get('/api/guidance/me/compare/?programs=bsbio,bsn,bscs')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual([row['program']['code'] for row in ok.data['programs']], ['bsbio', 'bsn', 'bscs'])
        self.assertEqual(self.client.get('/api/guidance/me/compare/?programs=bsbio').status_code, 400)
        self.assertEqual(self.client.get('/api/guidance/me/compare/?programs=bsbio,bsn,bscs,bsit').status_code, 400)


class StudentObjectAccessTests(GuidanceFixture, TestCase):
    """IDOR: no student endpoint takes an id, and no student can reach another student's data."""

    def setUp(self):
        super().setUp()
        self.ana = self.make_student('tech')
        self.ben = self.make_student('science')
        self.consent(self.ben)
        self.complete_assessment(self.ben, 'science')

    def test_each_student_sees_only_their_own_recommendation(self):
        ben_view = self.client_for(self.ben.user).get('/api/guidance/me/').data
        ana_view = self.client_for(self.ana.user).get('/api/guidance/me/').data
        self.assertEqual(RecommendationRun.objects.get(pk=ben_view['recommendation']['id']).student, self.ben)
        self.assertIsNone(ana_view['recommendation']['id'])
        self.assertFalse(ana_view['recommendation']['ready'])
        self.assertIsNone(ana_view['consent']['assessment'])

    def test_students_cannot_reach_adviser_or_admin_endpoints(self):
        client = self.client_for(self.ana.user)
        urls = [
            f'/api/guidance/advisory/{self.assignment.pk}/',
            f'/api/guidance/advisory/{self.assignment.pk}/students/{self.ben.pk}/',
            '/api/guidance/admin/catalog/',
            '/api/guidance/admin/recommender/',
            '/api/guidance/admin/outcomes/',
        ]
        for url in urls:
            self.assertEqual(client.get(url).status_code, 403, url)
        self.assertEqual(
            client.post(f'/api/guidance/advisory/{self.assignment.pk}/students/{self.ben.pk}/notes/', {'body': 'x'}).status_code,
            403,
        )

    def test_staff_cannot_use_student_endpoints(self):
        for user in (self.adviser, self.admin):
            self.assertEqual(self.client_for(user).get('/api/guidance/me/').status_code, 403)

    def test_signed_out_requests_are_refused(self):
        self.assertEqual(APIClient().get('/api/guidance/me/').status_code, 401)
        self.assertEqual(APIClient().get('/api/guidance/programs/').status_code, 401)
