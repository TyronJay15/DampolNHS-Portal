from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.grading.recommend import recommend_payload
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class GradeRow:
    def __init__(self, code, score):
        self.subject = type('Subject', (), {'code': code})()
        self.score = score


class CollegeKnnTests(SimpleTestCase):
    def test_same_section_strengths_pick_different_courses(self):
        ana = recommend_payload(
            [
                GradeRow('phys-1', '93'),
                GradeRow('chem-1', '91'),
                GradeRow('gen-math', '88'),
                GradeRow('eff-comm', '75'),
            ]
        )
        ben = recommend_payload(
            [
                GradeRow('gen-math', '90'),
                GradeRow('emtech', '94'),
                GradeRow('prog-java', '91'),
                GradeRow('phys-1', '76'),
            ]
        )
        cara = recommend_payload(
            [
                GradeRow('eff-comm', '92'),
                GradeRow('kasaysayan', '90'),
                GradeRow('gen-math', '78'),
                GradeRow('gen-sci', '74'),
            ]
        )
        self.assertTrue(ana['ready'])
        self.assertTrue(ben['ready'])
        self.assertTrue(cara['ready'])
        self.assertEqual(ana['courses'][0]['code'], 'bsce')
        self.assertEqual(ben['courses'][0]['code'], 'bscs')
        self.assertEqual(cara['courses'][0]['code'], 'bacom')
        self.assertEqual(len({ana['courses'][0]['code'], ben['courses'][0]['code'], cara['courses'][0]['code']}), 3)

    def test_too_few_skills_is_not_ready(self):
        payload = recommend_payload([GradeRow('gen-math', '90'), GradeRow('phys-1', '88')])
        self.assertFalse(payload['ready'])
        self.assertEqual(payload['courses'], [])


class StudentRecommendationApiTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEMC', name='STEM Cluster', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.math = Subject.objects.create(code='gen-math', name='General Mathematics')
        self.phys = Subject.objects.create(code='phys-1', name='Physics 1')
        self.chem = Subject.objects.create(code='chem-1', name='Chemistry 1')
        self.comm = Subject.objects.create(code='eff-comm', name='Effective Communication')
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

    def test_shown_card_includes_college_knn(self):
        self._release(self.phys, '93')
        self._release(self.chem, '91')
        self._release(self.math, '88')
        self._release(self.comm, '75')
        rec = self.client.get('/api/grades/me/').data['recommendation']
        self.assertEqual(rec['method'], 'knn')
        self.assertTrue(rec['ready'])
        self.assertEqual(rec['courses'][0]['code'], 'bsce')


class AdvisoryRecommendationTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        program = Program.objects.create(code='STEMC', name='STEM Cluster', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        math = Subject.objects.create(code='gen-math', name='General Mathematics')
        tech = Subject.objects.create(code='emtech', name='Empowerment Technologies')
        prog = Subject.objects.create(code='prog-java', name='Computer Programming (Java)')
        phys = Subject.objects.create(code='phys-1', name='Physics 1')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEMC-A',
            grade_level='Grade 11',
            program=program,
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
        student = StudentProfile.objects.create(user=student_user, lrn='136000009922')
        StudentSection.objects.create(student=student, section=self.section, school_year=self.year)
        for subject, score in ((math, '90'), (tech, '94'), (prog, '91'), (phys, '76')):
            Grade.objects.create(
                student=student,
                subject=subject,
                term=self.term,
                school_year=self.year,
                section=self.section,
                score=Decimal(score),
                status=Grade.Status.APPROVED,
            )
        self.advisory = TeacherAssignment.objects.create(
            teacher=self.adviser,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.adviser)

    def test_adviser_sees_college_match_from_approved_grades(self):
        response = self.client.get(
            f'/api/grades/advisory/?assignment={self.advisory.id}&term={self.term.id}'
        )
        self.assertEqual(response.status_code, 200)
        rec = response.data['students'][0]['recommendation']
        self.assertEqual(rec['method'], 'knn')
        self.assertEqual(rec['courses'][0]['code'], 'bscs')
