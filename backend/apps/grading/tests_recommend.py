from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.grading.recommend import recommend_payload, recommendation_grades
from apps.guidance.consent import NOTICE_VERSION
from apps.guidance.models import GuidanceConsent
from apps.ml.knn_model import METHOD
from apps.ml.models import CollegeProgram
from apps.ml.recommender import RecommenderContext
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


class CollegeMatchTests(TestCase):
    def setUp(self):
        self.subjects = {code: make_subject(code) for code in DOMAINS}

    def rows(self, scores):
        return [GradeRow(self.subjects[code], score) for code, score in scores]

    def payload(self, rows):
        return recommend_payload(rows, RecommenderContext())

    def test_same_section_strengths_pick_different_courses(self):
        ana = self.payload(self.rows([('phys-1', '93'), ('chem-1', '91'), ('gen-math', '88'), ('eff-comm', '75')]))
        ben = self.payload(self.rows([('gen-math', '90'), ('emtech', '94'), ('prog-java', '91'), ('phys-1', '76')]))
        cara = self.payload(self.rows([('eff-comm', '92'), ('kasaysayan', '90'), ('gen-math', '78'), ('gen-sci', '74')]))
        self.assertTrue(ana['ready'])
        self.assertTrue(ben['ready'])
        self.assertTrue(cara['ready'])
        self.assertEqual(strongest_domain(ana['courses'][0]['code']), 'science')
        self.assertEqual(strongest_domain(ben['courses'][0]['code']), 'tech')
        self.assertIn(strongest_domain(cara['courses'][0]['code']), ('language', 'social'))
        self.assertEqual(len({ana['courses'][0]['code'], ben['courses'][0]['code'], cara['courses'][0]['code']}), 3)

    def test_too_few_skills_is_not_ready(self):
        payload = self.payload(self.rows([('gen-math', '90'), ('phys-1', '88')]))
        self.assertFalse(payload['ready'])
        self.assertEqual(payload['courses'], [])


def make_subject_variant(status):
    return Subject.objects.create(code=f'gen-math-{status}', name=status, skill_domain=SkillDomain.objects.get(key='math'))


class EligibleGradesTests(TestCase):
    """The one eligibility rule: students read released grades, staff and training read approved and released."""

    def setUp(self):
        year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        term = Term.objects.create(school_year=year, number=1, label='Term 1')
        user = User.objects.create_user(email='rule@example.com', password='Strongpass1', role=User.Role.STUDENT)
        self.profile = StudentProfile.objects.create(user=user, lrn='136000009930')
        subject = make_subject('gen-math')
        for status in Grade.Status.values:
            Grade.objects.create(
                student=self.profile,
                subject=subject if status == Grade.Status.RELEASED else make_subject_variant(status),
                term=term,
                school_year=year,
                score=Decimal('90'),
                status=status,
            )

    def test_students_read_released_grades_only(self):
        rows = recommendation_grades([self.profile.pk], released_only=True)[self.profile.pk]
        self.assertEqual({row.status for row in rows}, {Grade.Status.RELEASED})

    def test_staff_read_approved_and_released_grades(self):
        rows = recommendation_grades([self.profile.pk], released_only=False)[self.profile.pk]
        self.assertEqual({row.status for row in rows}, {Grade.Status.APPROVED, Grade.Status.RELEASED})


class GradeCardTests(TestCase):
    def test_grade_card_no_longer_embeds_a_recommendation(self):
        """The student's College recommendation page owns recommendations; the card shows grades only."""
        year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        user = User.objects.create_user(email='card@example.com', password='Strongpass1', role=User.Role.STUDENT)
        StudentProfile.objects.create(user=user, lrn='136000009931')
        Term.objects.create(school_year=year, number=1, label='Term 1')
        client = APIClient()
        client.force_authenticate(user=user)
        self.assertNotIn('recommendation', client.get('/api/grades/me/').data)


class AdvisoryRecommendationTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='ICTP', name='ICT Programming', sort_order=1, strand_group='ICT')
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.section = Section.objects.create(
            school_year=self.year,
            name='ICTP-A',
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
        self.student_user = User.objects.create_user(
            email='ben@example.com',
            password='Strongpass1',
            first_name='Ben',
            last_name='Cruz',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000009922')
        StudentSection.objects.create(student=self.student, section=self.section, school_year=self.year)
        for code, score in (('gen-math', '90'), ('emtech', '94'), ('prog-java', '91'), ('phys-1', '76')):
            Grade.objects.create(
                student=self.student,
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
        CollegeProgram.objects.get(code='bsit').shs_programs.add(self.program)
        GuidanceConsent.objects.create(
            student=self.student,
            kind=GuidanceConsent.Kind.ASSESSMENT,
            party=GuidanceConsent.Party.STUDENT,
            notice_version=NOTICE_VERSION,
            active_marker=f'{self.student.pk}:assessment',
        )

    def advisory_rec(self):
        client = APIClient()
        client.force_authenticate(user=self.adviser)
        response = client.get(f'/api/grades/advisory/?assignment={self.advisory.id}&term={self.term.id}')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['students'][0]['recommendation']

    def test_adviser_sees_college_match(self):
        rec = self.advisory_rec()
        self.assertEqual(rec['method'], METHOD)
        self.assertEqual(strongest_domain(rec['courses'][0]['code']), 'tech')

    def test_advisory_endpoint_loads_with_the_full_recommendation_payload(self):
        rec = self.advisory_rec()
        self.assertTrue(rec['ready'])
        self.assertIn(rec['evidence'], ('strong', 'limited'))
        self.assertEqual(
            set(rec['coverage']),
            {'observed', 'dimensions', 'threshold', 'needs', 'not_evaluated', 'excluded_subjects', 'unmapped_subjects'},
        )
        top = rec['courses'][0]
        self.assertEqual(
            set(top),
            {'code', 'name', 'family', 'label', 'label_text', 'tier', 'distance', 'reason', 'strand_context', 'evidence'},
        )
        self.assertEqual(
            set(top['evidence']),
            {'status', 'observed', 'total', 'coverage', 'observed_domains', 'missing_domains'},
        )
        self.assertFalse(rec['model']['trained_on_outcomes'])
        bsit = next(row for row in rec['courses'] if row['code'] == 'bsit')
        self.assertEqual(bsit['strand_context'], 'typical')

    def test_student_adviser_and_admin_views_agree(self):
        """Every screen goes through the one ranking path, so the same released grades give the same order."""
        student = APIClient()
        student.force_authenticate(user=self.student_user)
        guidance = student.get('/api/guidance/me/').data['recommendation']
        admin = APIClient()
        admin.force_authenticate(
            user=User.objects.create_user(email='admin@dampol1nhs.edu.ph', password='changeme123', role=User.Role.ADMIN)
        )
        report = admin.get(f'/api/grades/report/?term={self.term.id}')
        self.assertEqual(report.status_code, 200)
        from_admin = report.data['sections'][0]['students'][0]['recommendation']
        from_adviser = self.advisory_rec()
        student_order = [item['program']['code'] for item in guidance['primary'] + guidance['additional']]
        self.assertEqual([row['code'] for row in from_adviser['courses']], student_order)
        self.assertEqual([row['code'] for row in from_admin['courses']], student_order)
        self.assertEqual(
            [row['label'] for row in from_adviser['courses']],
            [item['label'] for item in guidance['primary'] + guidance['additional']],
        )
