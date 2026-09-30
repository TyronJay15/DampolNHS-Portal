from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.ml.knn_model import METHOD
from apps.notifications.models import Notification
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class GradeWorkflowTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.subject = Subject.objects.create(code='gen-phys-1', name='General Physics 1')
        self.other_subject = Subject.objects.create(code='mil', name='Media and Information Literacy')
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
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000009921')
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
        self.teacher_client = APIClient()
        self.teacher_client.force_authenticate(user=self.teacher)
        self.adviser_client = APIClient()
        self.adviser_client.force_authenticate(user=self.adviser)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)
        self.head_client = APIClient()
        self.head_client.force_authenticate(user=self.head)

    def _submit_and_approve(self):
        self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        return self.head_client.post(
            '/api/grades/approve/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )

    def _mark_ptpa(self, attended=True, student=None):
        return self.adviser_client.post(
            '/api/grades/ptpa/',
            {
                'assignment': self.advisory.id,
                'term': self.term.id,
                'student': (student or self.student).id,
                'attended': attended,
            },
            format='json',
        )

    def _show(self, student=None):
        return self.adviser_client.post(
            '/api/grades/show/',
            {
                'assignment': self.advisory.id,
                'term': self.term.id,
                'student': (student or self.student).id,
            },
            format='json',
        )

    def _hide(self, student=None):
        return self.adviser_client.post(
            '/api/grades/hide/',
            {
                'assignment': self.advisory.id,
                'term': self.term.id,
                'student': (student or self.student).id,
            },
            format='json',
        )

    def test_submit_approve_show_hide_and_return(self):
        submit = self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': self.assignment.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(submit.status_code, 200)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.SUBMITTED)

        denied = self.admin_client.post(
            '/api/grades/approve/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        approve = self.head_client.post(
            '/api/grades/approve/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.data['approved'], 1)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.APPROVED)

        head_show = self.head_client.post(
            '/api/grades/show/',
            {'assignment': self.advisory.id, 'term': self.term.id, 'student': self.student.id},
            format='json',
        )
        self.assertEqual(head_show.status_code, 403)

        blocked = self._show()
        self.assertEqual(blocked.status_code, 200)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.RELEASED)

        student_client = APIClient()
        student_client.force_authenticate(user=self.student_user)
        seen = student_client.get('/api/grades/me/')
        self.assertEqual(len(seen.data['grades']), 1)
        self.assertEqual(seen.data['recommendation']['method'], METHOD)

        hide = self._hide()
        self.assertEqual(hide.data['hidden'], 1)
        hidden = student_client.get('/api/grades/me/')
        self.assertEqual(hidden.data['grades'], [])

        returned = self.head_client.post(
            '/api/grades/return/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        self.assertEqual(returned.data['returned'], 1)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.DRAFT)

    def test_can_show_partial_when_another_subject_is_missing(self):
        TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.other_subject,
            section=self.section,
        )
        self._submit_and_approve()
        shown = self._show()
        self.assertEqual(shown.status_code, 200, shown.data)
        self.assertEqual(shown.data['shown'], 1)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.RELEASED)
        student_client = APIClient()
        student_client.force_authenticate(user=self.student_user)
        card = student_client.get('/api/grades/me/')
        self.assertEqual(card.status_code, 200, card.data)
        self.assertTrue(card.data['partial'])
        self.assertIn('Partial card', card.data['coverage_note'])
        self.assertEqual(len(card.data['grades']), 1)
        self.assertTrue(any(row['name'] == 'Media and Information Literacy' for row in card.data['subjects']))

    def test_cannot_return_while_shown(self):
        self._submit_and_approve()
        self._show()
        response = self.head_client.post(
            '/api/grades/return/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_subject_teacher_cannot_show_advisory_card(self):
        self._submit_and_approve()
        response = self.teacher_client.post(
            '/api/grades/show/',
            {'assignment': self.advisory.id, 'term': self.term.id, 'student': self.student.id},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_show_one_student_does_not_release_the_other(self):
        other_user = User.objects.create_user(
            email='ben@example.com',
            password='Strongpass1',
            first_name='Ben',
            last_name='Cruz',
            role=User.Role.STUDENT,
        )
        other = StudentProfile.objects.create(user=other_user, lrn='136000009922')
        StudentSection.objects.create(student=other, section=self.section, school_year=self.year)
        Grade.objects.create(
            student=other,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('88.00'),
            status=Grade.Status.DRAFT,
            teacher=self.teacher,
        )
        self._submit_and_approve()
        self.assertEqual(self._show().status_code, 200)
        self.grade.refresh_from_db()
        other_grade = Grade.objects.get(student=other)
        self.assertEqual(self.grade.status, Grade.Status.RELEASED)
        self.assertEqual(other_grade.status, Grade.Status.APPROVED)

        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        self.assertEqual(other_client.get('/api/grades/me/').data['grades'], [])

        self.assertEqual(self._hide().status_code, 200)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.APPROVED)

    def test_return_hidden_student_leaves_shown_card(self):
        other_user = User.objects.create_user(
            email='ben2@example.com',
            password='Strongpass1',
            first_name='Ben',
            last_name='Cruz',
            role=User.Role.STUDENT,
        )
        other = StudentProfile.objects.create(user=other_user, lrn='136000009923')
        StudentSection.objects.create(student=other, section=self.section, school_year=self.year)
        Grade.objects.create(
            student=other,
            subject=self.subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('88.00'),
            status=Grade.Status.DRAFT,
            teacher=self.teacher,
        )
        self._submit_and_approve()
        self.assertEqual(self._show().status_code, 200)
        response = self.head_client.post(
            '/api/grades/return/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.subject.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['returned'], 1)
        self.assertEqual(response.data['still_shown'], 1)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.RELEASED)
        self.assertEqual(Grade.objects.get(student=other).status, Grade.Status.DRAFT)

    def test_show_ready_after_approval(self):
        self._submit_and_approve()
        ready = self.adviser_client.post(
            '/api/grades/show-ready/',
            {'assignment': self.advisory.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(ready.status_code, 200, ready.data)
        self.assertEqual(ready.data['shown'], 1)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.status, Grade.Status.RELEASED)

    def test_admin_class_report(self):
        self._submit_and_approve()
        response = self.admin_client.get('/api/grades/report/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['year']['label'], '2025-2026')
        section = response.data['sections'][0]
        self.assertEqual(section['name'], 'STEM-A')
        self.assertEqual(section['display_label'], '12 - STEM STEM-A')
        self.assertEqual(section['students'][0]['name'], 'Ana Reyes')
        self.assertEqual(section['adviser'], 'Rina Santos')

    def test_queue_lists_unencoded_assignment(self):
        TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.other_subject,
            section=self.section,
        )
        response = self.head_client.get(f'/api/grades/queues/?term={self.term.id}')
        self.assertEqual(response.status_code, 200, response.data)
        subjects = [
            item['subject']
            for teacher in response.data['teachers']
            for section in teacher['sections']
            for item in section['subjects']
        ]
        self.assertIn('Media and Information Literacy', subjects)
        mil = next(
            item
            for teacher in response.data['teachers']
            for section in teacher['sections']
            for item in section['subjects']
            if item['subject_id'] == self.other_subject.id
        )
        self.assertEqual(mil['progress'], 'not_encoded')
        self.assertEqual(mil['missing'], 1)

    def test_submit_notifies_adviser_when_card_is_shown(self):
        self._submit_and_approve()
        self.assertEqual(self._show().status_code, 200)
        mil = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.other_subject,
            section=self.section,
        )
        Grade.objects.create(
            student=self.student,
            subject=self.other_subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('88.00'),
            status=Grade.Status.DRAFT,
            teacher=self.teacher,
        )
        Notification.objects.filter(user=self.adviser).delete()
        submitted = self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': mil.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(submitted.status_code, 200, submitted.data)
        titles = list(Notification.objects.filter(user=self.adviser).values_list('title', flat=True))
        self.assertTrue(any('shown card' in title.lower() for title in titles), titles)

    def test_approve_notifies_adviser_to_reshow(self):
        self._submit_and_approve()
        self.assertEqual(self._show().status_code, 200)
        mil = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=self.other_subject,
            section=self.section,
        )
        Grade.objects.create(
            student=self.student,
            subject=self.other_subject,
            term=self.term,
            school_year=self.year,
            section=self.section,
            score=Decimal('88.00'),
            status=Grade.Status.DRAFT,
            teacher=self.teacher,
        )
        submitted = self.teacher_client.post(
            '/api/grades/submit/',
            {'assignment': mil.id, 'term': self.term.id},
            format='json',
        )
        self.assertEqual(submitted.status_code, 200, submitted.data)
        Notification.objects.filter(user=self.adviser).delete()
        approved = self.head_client.post(
            '/api/grades/approve/',
            {'term': self.term.id, 'section': self.section.id, 'subject': self.other_subject.id},
            format='json',
        )
        self.assertEqual(approved.status_code, 200, approved.data)
        titles = list(Notification.objects.filter(user=self.adviser).values_list('title', flat=True))
        self.assertTrue(any('re-show' in title.lower() for title in titles), titles)
