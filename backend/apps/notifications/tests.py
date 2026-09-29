from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.notifications.models import Notification
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class StudentNotificationTests(TestCase):
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
        self.teacher = User.objects.create_user(
            email='teacher@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
        )
        self.adviser = User.objects.create_user(
            email='adviser@dampol1nhs.edu.ph',
            password='Strongpass1',
            first_name='Rina',
            last_name='Santos',
            role=User.Role.TEACHER,
        )
        self.student_user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
        )
        other = User.objects.create_user(
            email='ben@example.com',
            password='Strongpass1',
            first_name='Ben',
            last_name='Cruz',
            role=User.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000009921')
        StudentProfile.objects.create(user=other, lrn='136000009922')
        StudentSection.objects.create(student=self.student, section=self.section, school_year=self.year)
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.subject,
            section=self.section,
        )
        self.advisory = TeacherAssignment.objects.create(
            teacher=self.adviser,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )
        self.grade = Grade.objects.create(
            student=self.student,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('90.00'),
            status=Grade.Status.DRAFT,
            teacher=self.teacher,
        )
        self.student_client = APIClient()
        self.student_client.force_authenticate(user=self.student_user)
        self.teacher_client = APIClient()
        self.teacher_client.force_authenticate(user=self.teacher)
        self.adviser_client = APIClient()
        self.adviser_client.force_authenticate(user=self.adviser)
        self.head_client = APIClient()
        self.head_client.force_authenticate(user=self.head)

    def _show(self):
        self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        self.head_client.post(
            '/api/grades/approve/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        return self.adviser_client.post(
            '/api/grades/show/',
            {'assignment': self.advisory.id, 'term': self.term.id, 'student': self.student.id},
            format='json',
        )

    def test_show_and_hide_notify_section_students_only(self):
        self.assertEqual(self._show().status_code, 200)
        inbox = self.student_client.get('/api/notifications/')
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(inbox.data['unread'], 1)
        self.assertEqual(inbox.data['notifications'][0]['title'], 'Report card available · Term 1')
        self.assertEqual(inbox.data['notifications'][0]['category'], 'grades')
        self.assertEqual(Notification.objects.filter(user=self.student_user).count(), 1)

        hide = self.adviser_client.post(
            '/api/grades/hide/',
            {'assignment': self.advisory.id, 'term': self.term.id, 'student': self.student.id},
            format='json',
        )
        self.assertEqual(hide.status_code, 200)
        inbox = self.student_client.get('/api/notifications/')
        self.assertEqual(inbox.data['unread'], 2)
        self.assertEqual(inbox.data['notifications'][0]['title'], 'Report card hidden · Term 1')

        teacher_titles = [row['title'] for row in self.teacher_client.get('/api/notifications/').data['notifications']]
        self.assertNotIn('Report card available · Term 1', teacher_titles)
        self.assertNotIn('Term 1 report card was hidden', teacher_titles)

    def test_student_can_mark_notifications_read(self):
        self._show()
        row = Notification.objects.get(user=self.student_user)
        marked = self.student_client.post(f'/api/notifications/{row.id}/read/')
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(marked.data['is_read'])
        inbox = self.student_client.get('/api/notifications/')
        self.assertEqual(inbox.data['unread'], 0)

        self.adviser_client.post(
            '/api/grades/hide/',
            {'assignment': self.advisory.id, 'term': self.term.id, 'student': self.student.id},
            format='json',
        )
        cleared = self.student_client.post('/api/notifications/read-all/')
        self.assertEqual(cleared.data['marked'], 1)
        self.assertEqual(self.student_client.get('/api/notifications/').data['unread'], 0)

    def test_deadline_notifies_teachers_in_the_year(self):
        closes = timezone.now() + timedelta(days=5)
        response = self.head_client.patch(
            f'/api/terms/{self.term.id}/',
            {'encode_closes_at': closes.isoformat()},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        inbox = self.student_client.get('/api/notifications/')
        self.assertEqual(inbox.data['unread'], 0)
        self.assertEqual(Notification.objects.filter(user=self.teacher).count(), 1)
        self.assertEqual(Notification.objects.get(user=self.teacher).title, 'Term 1 encode window')
