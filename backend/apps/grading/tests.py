from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.people.models import StudentSection
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class StudentDashboardApiTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.term = Term.objects.create(
            school_year=self.year,
            number=1,
            label='Term 1',
            status=Term.Status.ACTIVE,
            is_current=True,
        )
        self.subject = Subject.objects.create(code='math', name='Mathematics')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEM-A',
            grade_level='Grade 11',
            program=self.program,
        )
        self.user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.APPROVED,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            lrn='136000009921',
            contact_number='09171234567',
            grade_level='Grade 11',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_student_me_includes_section(self):
        StudentSection.objects.create(
            student=self.profile,
            section=self.section,
            school_year=self.year,
        )
        response = self.client.get('/api/students/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lrn'], '136000009921')
        self.assertEqual(response.data['section']['name'], 'STEM-A')

    def test_draft_grades_are_hidden(self):
        Grade.objects.create(
            student=self.profile,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            score=Decimal('90.00'),
            status=Grade.Status.DRAFT,
        )
        response = self.client.get('/api/grades/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['grades'], [])

    def test_released_grades_are_visible(self):
        Grade.objects.create(
            student=self.profile,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            score=Decimal('91.50'),
            status=Grade.Status.RELEASED,
            released_at=timezone.now(),
        )
        response = self.client.get('/api/grades/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['grades']), 1)
        self.assertEqual(response.data['grades'][0]['subject'], 'Mathematics')
        self.assertEqual(response.data['grades'][0]['term_number'], 1)
        self.assertEqual(response.data['terms'][0]['number'], 1)
        self.assertTrue(any(row['name'] == 'Mathematics' for row in response.data['subjects']))
        self.assertEqual(response.data['recommendation']['method'], 'knn')
