from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.grading.models import Grade
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class EncodeDeadlineTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.subject = Subject.objects.create(code='gen-phys-1', name='General Physics 1')
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEM-A',
            grade_level='Grade 12',
            program=program,
        )
        self.head = User.objects.create_user(
            email='head@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Helen',
            last_name='Cruz',
            role=User.Role.HEAD_TEACHER,
        )
        self.admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            first_name='School',
            last_name='Admin',
            role=User.Role.ADMIN,
        )
        self.teacher = User.objects.create_user(
            email='teacher@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
        )
        student_user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(user=student_user, lrn='136000009921')
        StudentSection.objects.create(student=self.student, section=self.section, school_year=self.year)
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.subject,
            section=self.section,
            grade_level='Grade 12',
        )
        self.client = APIClient()

    def _encode(self):
        self.client.force_authenticate(user=self.teacher)
        return self.client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '90',
            },
            format='json',
        )

    def test_open_window_allows_encode(self):
        response = self._encode()
        self.assertEqual(response.status_code, 200)

    def test_closed_window_blocks_encode_and_submit(self):
        self.term.encode_closes_at = timezone.now() - timedelta(minutes=1)
        self.term.save(update_fields=['encode_closes_at'])
        self.assertEqual(self._encode().status_code, 400)
        Grade.objects.create(
            student=self.student,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('88.00'),
            status=Grade.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.teacher)
        submit = self.client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(submit.status_code, 400)
        self.assertTrue(Grade.objects.filter(status=Grade.Status.DRAFT).exists())

    def test_head_teacher_sets_deadline_and_writes_audit(self):
        closes = timezone.now() + timedelta(days=7)
        self.client.force_authenticate(user=self.head)
        response = self.client.patch(
            f'/api/terms/{self.term.id}/',
            {'encode_closes_at': closes.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.term.refresh_from_db()
        self.assertIsNotNone(self.term.encode_closes_at)
        self.assertTrue(response.data['encode_open'])
        log = AuditLog.objects.get(action='deadline_set')
        self.assertEqual(log.actor_role, User.Role.HEAD_TEACHER)
        self.assertEqual(str(log.target_id), str(self.term.id))
        history = self.client.get(f'/api/terms/window-history/?school_year={self.year.id}')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data[0]['term'], self.term.label)

    def test_teacher_and_admin_cannot_set_deadline(self):
        self.client.force_authenticate(user=self.teacher)
        teacher = self.client.patch(
            f'/api/terms/{self.term.id}/',
            {'encode_closes_at': timezone.now().isoformat()},
            format='json',
        )
        self.assertEqual(teacher.status_code, 403)
        self.client.force_authenticate(user=self.admin)
        admin = self.client.patch(
            f'/api/terms/{self.term.id}/',
            {'encode_closes_at': timezone.now().isoformat()},
            format='json',
        )
        self.assertEqual(admin.status_code, 403)
