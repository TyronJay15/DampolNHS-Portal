"""Object-level access (security plan W21): the right role is not enough, the record must be the person's own.

Each test signs in as an allowed role and asks for someone else's record by changing an id.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access.models import AccessRequest, AccessTag
from apps.accounts.models import StudentProfile, User
from apps.cms.models import Announcement
from apps.grading.models import Grade
from apps.notifications.models import Notification
from apps.people.models import StudentSection, TeacherAssignment
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear, Section, Subject, Term


def make_user(email, role):
    return User.objects.create_user(
        email=email, password='Strongpass1!', first_name=email[0].upper(), last_name='Cruz', role=role,
        approval_status=User.ApprovalStatus.APPROVED, account_status=User.AccountStatus.ACTIVE,
    )


def as_user(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class ObjectAccessTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1', status='active', is_current=True)
        programs = make_programs()
        self.section_a = Section.objects.create(school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=programs['STEMC'])
        self.section_b = Section.objects.create(school_year=self.year, name='STEM-B', grade_level='Grade 12', program=programs['STEM'])
        self.subject = Subject.objects.create(code='gm', name='General Mathematics')
        self.teacher_a = make_user('a-teacher@x.com', User.Role.TEACHER)
        self.teacher_b = make_user('b-teacher@x.com', User.Role.TEACHER)
        self.student_a = self.student('a@x.com', '136000000001', self.section_a)
        self.student_b = self.student('b@x.com', '136000000002', self.section_b)
        self.adviser_a = TeacherAssignment.objects.create(
            teacher=self.teacher_a, assignment_type=TeacherAssignment.Type.ADVISER, status='active',
            school_year=self.year, section=self.section_a,
        )
        self.adviser_b = TeacherAssignment.objects.create(
            teacher=self.teacher_b, assignment_type=TeacherAssignment.Type.ADVISER, status='active',
            school_year=self.year, section=self.section_b,
        )
        self.class_b = TeacherAssignment.objects.create(
            teacher=self.teacher_b, assignment_type='subject_teacher', status='active',
            school_year=self.year, section=self.section_b, subject=self.subject,
        )

    def student(self, email, lrn, section):
        user = make_user(email, User.Role.STUDENT)
        profile = StudentProfile.objects.create(user=user, lrn=lrn, grade_level=section.grade_level)
        StudentSection.objects.create(student=profile, section=section, school_year=self.year)
        return profile

    def test_nobody_can_mark_someone_elses_notification(self):
        theirs = Notification.objects.create(user=self.student_b.user, title='Grades', body='Shown')
        response = as_user(self.student_a.user).post(f'/api/notifications/{theirs.pk}/read/')
        self.assertEqual(response.status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)

    def test_a_student_prints_only_their_own_card(self):
        response = as_user(self.student_a.user).get(f'/api/grades/print/?student={self.student_b.pk}')
        self.assertEqual(response.data['student']['lrn'], self.student_a.lrn)

    def test_an_adviser_cannot_open_another_sections_student(self):
        client = as_user(self.teacher_a)
        own_assignment_other_student = client.get(f'/api/guidance/advisory/{self.adviser_a.pk}/students/{self.student_b.pk}/')
        other_assignment = client.get(f'/api/guidance/advisory/{self.adviser_b.pk}/students/{self.student_b.pk}/')
        note = client.post(
            f'/api/guidance/advisory/{self.adviser_b.pk}/students/{self.student_b.pk}/notes/', {'body': 'x'}, format='json'
        )
        self.assertEqual(
            (own_assignment_other_student.status_code, other_assignment.status_code, note.status_code), (404, 404, 404)
        )

    def test_a_teacher_cannot_read_or_change_another_teachers_class(self):
        client = as_user(self.teacher_a)
        read = client.get(f'/api/grades/class/?assignment={self.class_b.pk}&term={self.term.pk}')
        encode = client.post(
            '/api/grades/encode/',
            {'assignment': self.class_b.pk, 'term': self.term.pk, 'student': self.student_b.pk, 'score': 99},
            format='json',
        )
        self.assertEqual((read.status_code, encode.status_code), (403, 403))
        self.assertFalse(Grade.objects.exists())

    def test_a_head_teacher_cannot_approve_outside_their_grade_levels(self):
        head = make_user('head@x.com', User.Role.HEAD_TEACHER)
        TeacherAssignment.objects.create(
            teacher=head, assignment_type=TeacherAssignment.Type.HEAD_TEACHER, status='active',
            school_year=self.year, grade_level='Grade 11',
        )
        grade = Grade.objects.create(
            student=self.student_b, subject=self.subject, term=self.term, school_year=self.year, section=self.section_b,
            teacher=self.teacher_b, score=Decimal('90'), status=Grade.Status.SUBMITTED,
        )
        response = as_user(head).post('/api/grades/approve/', {'term': self.term.pk, 'section': self.section_b.pk}, format='json')
        self.assertEqual(response.data['approved'], 0)
        grade.refresh_from_db()
        self.assertEqual(grade.status, Grade.Status.SUBMITTED)

    def test_only_the_proposer_can_withdraw_an_access_request(self):
        admin = make_user('admin@x.com', User.Role.ADMIN)
        tag = AccessTag.objects.create(holder=self.teacher_b, activity='review_registrations', granted_by=admin)
        request = AccessRequest.objects.create(
            tag=tag, activity='review_registrations', requested_by=self.teacher_b, payload={}, summary='x',
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = as_user(self.teacher_a).post(f'/api/access/requests/{request.pk}/withdraw/')
        self.assertIn(response.status_code, (403, 404))
        request.refresh_from_db()
        self.assertEqual(request.status, AccessRequest.Status.PENDING)

    def test_a_draft_announcement_cannot_be_read_by_guessing_its_id(self):
        draft = Announcement.objects.create(title='Not yet', body='Draft text', is_published=False)
        self.assertEqual(APIClient().get(f'/api/announcements/{draft.pk}/').status_code, 404)
        self.assertEqual(as_user(self.student_a.user).get(f'/api/announcements/{draft.pk}/').status_code, 404)
