from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.people.models import Registration
from apps.school.models import Program, ProgramSubject, SchoolYear, Section, Subject
from apps.school.offerings import seed_programs, sync_subject_catalog
from apps.school.subject_catalog import SUBJECT_NAMES


def seed_programs_and_subjects():
    seed_programs()
    sync_subject_catalog()


class SubjectCatalogTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        seed_programs_and_subjects()
        self.ash = Program.objects.get(code='ASH')
        self.stem = Program.objects.get(code='STEM')
        self.head = User.objects.create_user(
            email='head@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Helen',
            last_name='Cruz',
            role=User.Role.HEAD_TEACHER,
        )
        self.teacher = User.objects.create_user(
            email='teacher@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.head)

    def test_setup_replaces_legacy_cores(self):
        Subject.objects.create(code='math', name='Mathematics')
        sync_subject_catalog()
        self.assertFalse(Subject.objects.get(code='math').is_active)
        self.assertTrue(Subject.objects.filter(code='eff-comm', is_active=True).exists())
        self.assertTrue(Subject.objects.filter(code='mab-kom', is_active=True).exists())

    def test_ash_includes_cores_not_stemc_labs(self):
        names = set(
            ProgramSubject.objects.filter(program=self.ash).values_list('subject__code', flat=True)
        )
        self.assertIn('eff-comm', names)
        self.assertIn('ph-governance', names)
        self.assertNotIn('bio-1', names)

    def test_programs_api_returns_catalog_subjects(self):
        response = self.client.get('/api/programs/')
        self.assertEqual(response.status_code, 200)
        ash = next(row for row in response.data if row['code'] == 'ASH')
        names = [item['name'] for item in ash['subjects']]
        self.assertIn(SUBJECT_NAMES['eff-comm'], names)
        self.assertIn(SUBJECT_NAMES['soc-sci'], names)
        self.assertNotIn(SUBJECT_NAMES['bio-1'], names)

    def test_subjects_filter_by_program(self):
        response = self.client.get('/api/subjects/?program=BE')
        self.assertEqual(response.status_code, 200)
        codes = {row['code'] for row in response.data}
        self.assertIn('bus-1', codes)
        self.assertNotIn('bio-1', codes)

    def test_cannot_create_grade11_stem_section(self):
        response = self.client.post(
            '/api/sections/',
            {
                'name': 'STEM-A',
                'grade_level': 'Grade 11',
                'school_year': self.year.id,
                'program': self.stem.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_assign_off_program_subject(self):
        section = Section.objects.create(
            school_year=self.year,
            name='ASH-A',
            grade_level='Grade 11',
            program=self.ash,
        )
        biology = Subject.objects.get(code='bio-1')
        response = self.client.post(
            '/api/admin/assignments/',
            {
                'teacher': self.teacher.id,
                'type': 'subject_teacher',
                'section': section.id,
                'subject': biology.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_student_me_loads_enrolled_program_subjects(self):
        student = User.objects.create_user(
            email='jeff@example.com',
            password='Strongpass1',
            first_name='Jeff',
            last_name='Cruz',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.APPROVED,
        )
        StudentProfile.objects.create(user=student, lrn='136000009922', grade_level='Grade 11')
        Registration.objects.create(
            user=student,
            school_year=self.year,
            program=self.ash,
            grade_level_enrollment='Grade 11',
            status=Registration.Status.APPROVED,
        )
        client = APIClient()
        client.force_authenticate(user=student)
        response = client.get('/api/students/me/')
        self.assertEqual(response.status_code, 200)
        codes = {row['code'] for row in response.data['subjects']}
        self.assertIn('eff-comm', codes)
        self.assertIn('mab-kom', codes)
        self.assertIn('ph-governance', codes)
        self.assertNotIn('bio-1', codes)
        self.assertNotIn('gen-phys-1', codes)
