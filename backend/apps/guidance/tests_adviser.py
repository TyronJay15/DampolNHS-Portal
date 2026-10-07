"""The adviser's guidance tab: own section only, separate records, outcomes for training."""

from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.guidance.models import AdviserRecommendation, RecommendationItem, RecommendationRun
from apps.guidance.testing import GuidanceFixture
from apps.ml.models import CollegeOutcome, CollegeProgram
from apps.people.models import TeacherAssignment
from apps.school.models import Section


class AdviserAccessTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student('tech')
        self.other_section = Section.objects.create(school_year=self.year, name='B', grade_level='Grade 12', program=self.shs_program)
        self.outsider = self.make_student('science', section=self.other_section)
        self.client = self.client_for(self.adviser)
        self.base = f'/api/guidance/advisory/{self.assignment.pk}/'

    def test_roster_lists_only_the_advisers_section(self):
        data = self.client.get(self.base).data
        self.assertEqual([row['student_id'] for row in data['students']], [self.student.pk])

    def test_a_student_from_another_section_is_not_found(self):
        self.assertEqual(self.client.get(f'{self.base}students/{self.outsider.pk}/').status_code, 404)
        self.assertEqual(
            self.client.post(f'{self.base}students/{self.outsider.pk}/notes/', {'body': 'x'}, format='json').status_code,
            404,
        )

    def test_another_teachers_assignment_is_not_found(self):
        stranger = self.make_user(User.Role.TEACHER, 'stranger')
        client = self.client_for(stranger)
        self.assertEqual(client.get(self.base).status_code, 404)
        self.assertEqual(client.get(f'{self.base}students/{self.student.pk}/').status_code, 404)

    def test_an_ended_assignment_no_longer_gives_access(self):
        TeacherAssignment.objects.filter(pk=self.assignment.pk).update(status=TeacherAssignment.Status.ENDED)
        self.assertEqual(self.client.get(self.base).status_code, 404)

    def test_review_shows_the_students_run_and_is_audited(self):
        self.consent(self.student)
        response = self.client.get(f'{self.base}students/{self.student.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['recommendation']['ready'])
        self.assertTrue(AuditLog.objects.filter(action='guidance_student_viewed', target_id=str(self.student.pk)).exists())


class AdviserRecordTests(GuidanceFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.student = self.make_student('tech')
        self.client = self.client_for(self.adviser)
        self.url = f'/api/guidance/advisory/{self.assignment.pk}/students/{self.student.pk}/'

    def test_adviser_recommendation_never_changes_the_system_result(self):
        self.consent(self.student)
        self.client.get(self.url)
        run = RecommendationRun.objects.get(student=self.student)
        before = list(RecommendationItem.objects.filter(run=run).values_list('college_program__code', 'rank', 'label'))
        response = self.client.post(
            f'{self.url}recommendation/',
            {'program': 'bsce', 'reason': 'Stronger engineering interest in advising.'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        after = list(RecommendationItem.objects.filter(run=run).values_list('college_program__code', 'rank', 'label'))
        self.assertEqual(before, after)
        record = AdviserRecommendation.objects.get(student=self.student)
        self.assertEqual((record.college_program.code, record.run), ('bsce', run))
        self.assertEqual(response.data['adviser_recommendations'][0]['program']['code'], 'bsce')

    def test_adviser_recommendation_needs_an_active_program_and_a_reason(self):
        self.assertEqual(self.client.post(f'{self.url}recommendation/', {'program': 'bsce'}, format='json').status_code, 400)
        self.assertEqual(
            self.client.post(f'{self.url}recommendation/', {'program': 'nope', 'reason': 'x'}, format='json').status_code,
            400,
        )

    def test_notes_are_kept_and_bounded(self):
        self.assertEqual(self.client.post(f'{self.url}notes/', {'body': ''}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'{self.url}notes/', {'body': 'x' * 2001}, format='json').status_code, 400)
        response = self.client.post(f'{self.url}notes/', {'body': 'Discussed nursing and IT.'}, format='json')
        self.assertEqual(response.data['notes'][0]['body'], 'Discussed nursing and IT.')

    def test_outcome_is_recorded_then_validated_by_a_second_person(self):
        self.client.post(f'{self.url}outcome/', {'program': 'bsit'}, format='json')
        outcome = CollegeOutcome.objects.get(student=self.student)
        self.assertEqual((outcome.status, outcome.recorded_by), (CollegeOutcome.Status.RECORDED, self.adviser))
        admin = self.client_for(self.admin)
        self.assertEqual(admin.post(f'/api/guidance/admin/outcomes/{outcome.pk}/validate/').status_code, 200)
        outcome.refresh_from_db()
        self.assertEqual(outcome.status, CollegeOutcome.Status.VALIDATED)
        refused = self.client.post(f'{self.url}outcome/', {'program': 'bscs'}, format='json')
        self.assertEqual(refused.status_code, 400)

    def test_the_recorder_cannot_validate_their_own_outcome(self):
        CollegeOutcome.objects.create(
            student=self.student,
            college_program=CollegeProgram.objects.get(code='bsit'),
            school_year=self.year,
            recorded_by=self.admin,
        )
        outcome = CollegeOutcome.objects.get(student=self.student)
        response = self.client_for(self.admin).post(f'/api/guidance/admin/outcomes/{outcome.pk}/validate/')
        self.assertEqual(response.status_code, 400)
