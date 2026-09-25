from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class TeacherEncodeTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.subject = Subject.objects.create(code='math', name='Mathematics')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEM-A',
            grade_level='Grade 11',
            program=program,
        )
        self.teacher = User.objects.create_user(
            email='teacher@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
        )
        self.other = User.objects.create_user(
            email='other@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Other',
            last_name='Teacher',
            role=User.Role.TEACHER,
        )
        self.student_user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000009921')
        StudentSection.objects.create(student=self.student, section=self.section, school_year=self.year)
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.subject,
            section=self.section,
            grade_level='Grade 11',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def test_lists_own_assignments(self):
        response = self.client.get('/api/teachers/assignments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['can_encode'])

    def test_cannot_encode_another_teachers_class(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '90',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_encodes_draft_grade_for_assigned_class(self):
        roster = self.client.get(
            f'/api/grades/class/?assignment={self.assignment.id}&term={self.term.id}'
        )
        self.assertEqual(roster.status_code, 200)
        self.assertEqual(len(roster.data['students']), 1)

        encode = self.client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '91.5',
            },
            format='json',
        )
        self.assertEqual(encode.status_code, 200)
        grade = Grade.objects.get(student=self.student, subject=self.subject, term=self.term)
        self.assertEqual(grade.status, Grade.Status.DRAFT)
        self.assertEqual(grade.score, Decimal('91.50'))

    def test_cannot_change_released_grade(self):
        Grade.objects.create(
            student=self.student,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            score=Decimal('80.00'),
            status=Grade.Status.RELEASED,
        )
        response = self.client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '99',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
