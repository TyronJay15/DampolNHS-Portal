from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.grading.models import CorrectionRequest, Grade, GradeHistory
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class GradeIntegrityTests(TestCase):
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
        self.admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            first_name='School',
            last_name='Admin',
            role=User.Role.ADMIN,
        )
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
        )
        self.teacher_client = APIClient()
        self.teacher_client.force_authenticate(user=self.teacher)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)
        self.head_client = APIClient()
        self.head_client.force_authenticate(user=self.head)

    def test_encode_and_submit_write_history_and_audit(self):
        encode = self.teacher_client.post(
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
        history = GradeHistory.objects.get(to_status=Grade.Status.DRAFT)
        self.assertEqual(history.duty, 'subject_teacher')
        self.assertEqual(history.new_score, Decimal('91.50'))
        self.assertTrue(AuditLog.objects.filter(action='grade_encoded').exists())

        submit = self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(submit.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action='grades_submitted').exists())
        self.assertTrue(GradeHistory.objects.filter(to_status=Grade.Status.SUBMITTED, duty='subject_teacher').exists())

    def test_admin_reads_history_teacher_cannot(self):
        self.teacher_client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '88',
            },
            format='json',
        )
        denied = self.teacher_client.get('/api/grades/history/')
        self.assertEqual(denied.status_code, 403)
        allowed = self.admin_client.get('/api/grades/history/')
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data[0]['lrn'], '136000009921')
        self.assertEqual(allowed.data[0]['duty'], 'subject_teacher')

    def test_correction_changes_score_and_writes_trail(self):
        self.teacher_client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '80',
            },
            format='json',
        )
        self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        grade = Grade.objects.get(student=self.student, subject=self.subject, term=self.term)
        request = self.teacher_client.post(
            '/api/grades/corrections/',
            {
                'assignment': self.assignment.id,
                'grade': grade.id,
                'proposed_score': '85',
                'reason': 'Rechecked the quiz total.',
            },
            format='json',
        )
        self.assertEqual(request.status_code, 201)
        self.assertTrue(AuditLog.objects.filter(action='correction_requested').exists())

        review = self.head_client.post(
            f'/api/grades/corrections/{request.data["id"]}/review/',
            {'status': CorrectionRequest.Status.APPROVED},
            format='json',
        )
        self.assertEqual(review.status_code, 200)
        grade.refresh_from_db()
        self.assertEqual(grade.score, Decimal('85.00'))
        self.assertTrue(GradeHistory.objects.filter(reason='Head teacher approved correction', duty='head_teacher').exists())
        self.assertTrue(AuditLog.objects.filter(action='correction_approved').exists())

    def test_history_is_not_editable(self):
        self.teacher_client.post(
            '/api/grades/encode/',
            {
                'assignment': self.assignment.id,
                'term': self.term.id,
                'student': self.student.id,
                'score': '70',
            },
            format='json',
        )
        row = GradeHistory.objects.get()
        row.reason = 'tampered'
        with self.assertRaises(PermissionError):
            row.save()
