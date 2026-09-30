from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.grading.recommend import recommend_payload
from apps.ml.knn_model import METHOD
from apps.ml.models import CollegeProgram
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, SkillDomain, Subject, Term

DOMAINS = {
    'phys-1': 'science',
    'chem-1': 'science',
    'gen-sci': 'science',
    'gen-math': 'math',
    'eff-comm': 'language',
    'kasaysayan': 'social',
    'emtech': 'tech',
    'prog-java': 'tech',
}


def make_subject(code):
    return Subject.objects.create(code=code, name=code, skill_domain=SkillDomain.objects.get(key=DOMAINS[code]))


def strongest_domain(college_code):
    program = CollegeProgram.objects.get(code=college_code)
    return max(program.skills.all(), key=lambda row: row.level).domain.key


class GradeRow:
    def __init__(self, subject, score):
        self.subject = subject
        self.subject_id = subject.pk
        self.score = score


class CollegeKnnTests(TestCase):
    def setUp(self):
        self.subjects = {code: make_subject(code) for code in DOMAINS}

    def rows(self, scores):
        return [GradeRow(self.subjects[code], score) for code, score in scores]

    def test_same_section_strengths_pick_different_courses(self):
        ana = recommend_payload(self.rows([('phys-1', '93'), ('chem-1', '91'), ('gen-math', '88'), ('eff-comm', '75')]))
        ben = recommend_payload(self.rows([('gen-math', '90'), ('emtech', '94'), ('prog-java', '91'), ('phys-1', '76')]))
        cara = recommend_payload(self.rows([('eff-comm', '92'), ('kasaysayan', '90'), ('gen-math', '78'), ('gen-sci', '74')]))
        self.assertTrue(ana['ready'])
        self.assertTrue(ben['ready'])
        self.assertTrue(cara['ready'])
        self.assertEqual(strongest_domain(ana['courses'][0]['code']), 'science')
        self.assertEqual(strongest_domain(ben['courses'][0]['code']), 'tech')
        self.assertIn(strongest_domain(cara['courses'][0]['code']), ('language', 'social'))
        self.assertEqual(len({ana['courses'][0]['code'], ben['courses'][0]['code'], cara['courses'][0]['code']}), 3)

    def test_too_few_skills_is_not_ready(self):
        payload = recommend_payload(self.rows([('gen-math', '90'), ('phys-1', '88')]))
        self.assertFalse(payload['ready'])
        self.assertEqual(payload['courses'], [])


class StudentRecommendationApiTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEMC', name='STEM Cluster', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.math = make_subject('gen-math')
        self.phys = make_subject('phys-1')
        self.chem = make_subject('chem-1')
        self.comm = make_subject('eff-comm')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEMC-A',
            grade_level='Grade 11',
            program=self.program,
        )
        self.user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
        )
        self.profile = StudentProfile.objects.create(user=self.user, lrn='136000009921')
        StudentSection.objects.create(student=self.profile, section=self.section, school_year=self.year)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _release(self, subject, score):
        Grade.objects.create(
            student=self.profile,
            subject=subject,
            term=self.term,
            school_year=self.year,
            score=Decimal(score),
            status=Grade.Status.RELEASED,
        )

    def test_hidden_card_has_no_recommendation(self):
        Grade.objects.create(
            student=self.profile,
            subject=self.phys,
            term=self.term,
            school_year=self.year,
            score=Decimal('90.00'),
            status=Grade.Status.APPROVED,
        )
        response = self.client.get('/api/grades/me/')
        self.assertEqual(response.data['recommendation'], None)

    def test_shown_card_includes_college_match(self):
        self._release(self.phys, '93')
        self._release(self.chem, '91')
        self._release(self.math, '88')
        self._release(self.comm, '75')
        rec = self.client.get('/api/grades/me/').data['recommendation']
        self.assertEqual(rec['method'], METHOD)
        self.assertTrue(rec['ready'])
        self.assertEqual(strongest_domain(rec['courses'][0]['code']), 'science')


class AdvisoryRecommendationTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEMC', name='STEM Cluster', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEMC-A',
            grade_level='Grade 11',
            program=self.program,
        )
        self.adviser = User.objects.create_user(
            email='adviser@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Rina',
            last_name='Santos',
            role=User.Role.TEACHER,
        )
        student_user = User.objects.create_user(
            email='ben@example.com',
            password='Strongpass1',
            first_name='Ben',
            last_name='Cruz',
            role=User.Role.STUDENT,
        )
        self.student_user = student_user
        student = StudentProfile.objects.create(user=student_user, lrn='136000009922')
        StudentSection.objects.create(student=student, section=self.section, school_year=self.year)
        for code, score in (('gen-math', '90'), ('emtech', '94'), ('prog-java', '91'), ('phys-1', '76')):
            Grade.objects.create(
                student=student,
                subject=make_subject(code),
                term=self.term,
                school_year=self.year,
                section=self.section,
                score=Decimal(score),
                status=Grade.Status.RELEASED,
            )
        self.advisory = TeacherAssignment.objects.create(
            teacher=self.adviser,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )
        # The track boost only matters if the student's program leads to a course.
        CollegeProgram.objects.get(code='bsit').shs_programs.add(self.program)

    def test_adviser_sees_college_match(self):
        client = APIClient()
        client.force_authenticate(user=self.adviser)
        response = client.get(f'/api/grades/advisory/?assignment={self.advisory.id}&term={self.term.id}')
        self.assertEqual(response.status_code, 200)
        rec = response.data['students'][0]['recommendation']
        self.assertEqual(rec['method'], METHOD)
        self.assertEqual(strongest_domain(rec['courses'][0]['code']), 'tech')

    def test_advisory_endpoint_loads_with_the_full_recommendation_payload(self):
        """Regression: GET /api/grades/advisory/ raised ValueError when rank() and its caller disagreed."""
        client = APIClient()
        client.force_authenticate(user=self.adviser)
        response = client.get(f'/api/grades/advisory/?assignment={self.advisory.id}&term={self.term.id}')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['students']), 1)
        rec = response.data['students'][0]['recommendation']
        self.assertTrue(rec['ready'])
        self.assertIn(rec['evidence'], ('strong', 'limited'))
        self.assertEqual(
            set(rec['coverage']),
            {'observed', 'dimensions', 'threshold', 'needs', 'not_evaluated', 'excluded_subjects', 'unmapped_subjects'},
        )
        self.assertIsInstance(rec['coverage']['not_evaluated'], int)
        self.assertIsInstance(rec['coverage']['needs'], list)
        top = rec['courses'][0]
        self.assertEqual(set(top), {'code', 'name', 'distance', 'reason', 'track_match', 'evidence'})
        self.assertEqual(
            set(top['evidence']),
            {'status', 'observed', 'total', 'coverage', 'observed_domains', 'missing_domains'},
        )
        self.assertTrue(top['track_match'])
        self.assertFalse(rec['model']['trained_on_outcomes'])

    def test_student_adviser_and_admin_views_agree(self):
        """Every screen passes the student's program, so the same grades give the same result."""
        adviser = APIClient()
        adviser.force_authenticate(user=self.adviser)
        student = APIClient()
        student.force_authenticate(user=self.student_user)
        admin = APIClient()
        admin.force_authenticate(
            user=User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        )
        from_adviser = adviser.get(f'/api/grades/advisory/?assignment={self.advisory.id}&term={self.term.id}').data
        from_student = student.get('/api/grades/me/').data
        report = admin.get(f'/api/grades/report/?term={self.term.id}')
        self.assertEqual(report.status_code, 200)
        from_admin = report.data['sections'][0]['students'][0]['recommendation']
        self.assertEqual(from_adviser['students'][0]['recommendation'], from_student['recommendation'])
        self.assertEqual(from_admin, from_student['recommendation'])
        top = from_student['recommendation']['courses'][0]
        self.assertIn(top['evidence']['status'], ('strong', 'limited'))
        self.assertEqual(from_admin['evidence'], top['evidence']['status'])
        self.assertEqual(from_adviser['students'][0]['recommendation']['courses'][0]['evidence'], top['evidence'])
