from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.cms.models import SiteContent
from apps.notifications.models import Notification
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.people.views_school import TRANSFER_TITLE
from apps.school.models import Program, ProgramSubject, SchoolYear, Section, SkillDomain, Subject, Term


class AdminSchoolCmsTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEM-A',
            grade_level='Grade 12',
            program=self.program,
        )
        self.subject = Subject.objects.create(code='gen-phys-1', name='General Physics 1')
        ProgramSubject.objects.create(
            program=self.program,
            subject=self.subject,
            kind=ProgramSubject.Kind.SPECIALIZED,
            term=1,
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
            approval_status=User.ApprovalStatus.APPROVED,
        )
        self.student = StudentProfile.objects.create(user=student_user, lrn='136000009921')
        self.client = APIClient()
        self.client.force_authenticate(user=self.head)

    def test_head_teacher_creates_school_year_with_terms(self):
        response = self.client.post(
            '/api/school-years/',
            {'label': '2026-2027', 'is_current': False},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Term.objects.filter(school_year_id=response.data['id']).count(), 3)

    def test_place_student_in_section(self):
        response = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': self.section.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['section'], '12 - STEM STEM-A')

    def test_assign_subject_teacher(self):
        response = self.client.post(
            '/api/admin/assignments/',
            {
                'teacher': self.teacher.id,
                'type': 'subject_teacher',
                'section': self.section.id,
                'subject': self.subject.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(TeacherAssignment.objects.filter(teacher=self.teacher, subject=self.subject).exists())

    def test_end_teacher_assignment(self):
        created = self.client.post(
            '/api/admin/assignments/',
            {
                'teacher': self.teacher.id,
                'type': 'subject_teacher',
                'section': self.section.id,
                'subject': self.subject.id,
            },
            format='json',
        )
        response = self.client.delete(f'/api/admin/assignments/{created.data["id"]}/')
        self.assertEqual(response.status_code, 200)
        row = TeacherAssignment.objects.get(pk=created.data['id'])
        self.assertEqual(row.status, TeacherAssignment.Status.ENDED)

    def test_admin_cannot_place_student(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': self.section.id},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_assign_head_teacher_duty(self):
        response = self.client.post(
            '/api/admin/assignments/',
            {
                'teacher': self.teacher.id,
                'type': 'head_teacher',
                'section': self.section.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_head_teacher_creates_section(self):
        response = self.client.post(
            '/api/sections/',
            {
                'name': 'STEM-B',
                'grade_level': 'Grade 12',
                'school_year': self.year.id,
                'program': self.program.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['name'], 'STEM-B')
        self.assertEqual(response.data['display_label'], '12 - STEM STEM-B')

    def test_cannot_delete_busy_year(self):
        response = self.client.delete(f'/api/school-years/{self.year.id}/delete/')
        self.assertEqual(response.status_code, 400)

    def test_archive_and_restore_empty_ready_year(self):
        created = self.client.post(
            '/api/school-years/',
            {'label': '2027-2028', 'is_current': False},
            format='json',
        )
        year_id = created.data['id']
        archived = self.client.post(f'/api/school-years/{year_id}/archive/')
        self.assertEqual(archived.status_code, 200, archived.data)
        self.assertTrue(archived.data['archived'])
        restored = self.client.post(f'/api/school-years/{year_id}/restore/')
        self.assertEqual(restored.status_code, 200, restored.data)
        self.assertFalse(restored.data['archived'])
        deleted = self.client.delete(f'/api/school-years/{year_id}/delete/')
        self.assertEqual(deleted.status_code, 200, deleted.data)

    def test_save_cms_about(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            '/api/cms/content/',
            {'document': 'about', 'payload': {'title': 'Updated about title', 'mission': 'Serve learners.'}},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteContent.objects.get(document='about').payload['title'], 'Updated about title')

    def test_publish_announcement_sets_timestamp(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/announcements/',
            {'title': 'Enrollment notice', 'body': 'Bring requirements.', 'is_published': True},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_published'])
        self.assertIsNotNone(response.data['published_at'])

    def test_archived_student_hidden_from_placements(self):
        self.student.user.account_status = User.AccountStatus.ARCHIVED
        self.student.user.save(update_fields=['account_status'])
        response = self.client.get('/api/admin/placements/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.student.id, [row['student_id'] for row in response.data])

    def test_transfer_allows_program_change_and_notifies_advisers(self):
        Registration.objects.create(
            user=self.student.user,
            school_year=self.year,
            program=self.program,
            grade_level_enrollment='Grade 12',
            status=Registration.Status.APPROVED,
        )
        other_program = Program.objects.create(code='HUMSS', name='HUMSS', sort_order=2)
        target = Section.objects.create(
            school_year=self.year,
            name='HUMSS-A',
            grade_level='Grade 12',
            program=other_program,
        )
        TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )
        placed = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': self.section.id},
            format='json',
        )
        self.assertEqual(placed.status_code, 200, placed.data)
        blocked = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': target.id},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)
        moved = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': target.id, 'transfer': True},
            format='json',
        )
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertTrue(Notification.objects.filter(user=self.teacher, title=TRANSFER_TITLE).exists())
        registration = Registration.objects.get(user=self.student.user)
        self.assertEqual(registration.program, other_program)
        self.assertTrue(
            StudentSection.objects.filter(student=self.student, section=target, is_active=True).exists()
        )

    def test_grade_must_match_program_everywhere(self):
        grade12 = Program.objects.create(code='ABM', name='ABM', grade_level='Grade 12', sort_order=3)
        with self.assertRaises(ValidationError):
            Registration.objects.create(
                user=self.student.user,
                school_year=self.year,
                program=grade12,
                grade_level_enrollment='Grade 11',
            )
        with self.assertRaises(ValidationError):
            Section.objects.create(school_year=self.year, name='ABM-X', grade_level='Grade 11', program=grade12)
        Subject.objects.update(skill_domain=SkillDomain.objects.get(key='science'))
        call_command('check_data', stdout=StringIO())
        Section.objects.bulk_create(
            [Section(school_year=self.year, name='ABM-Y', grade_level='Grade 11', program=grade12)]
        )
        with self.assertRaises(CommandError):
            call_command('check_data', stdout=StringIO())

    def test_transfer_respects_target_capacity(self):
        Registration.objects.create(
            user=self.student.user,
            school_year=self.year,
            program=self.program,
            grade_level_enrollment='Grade 12',
            status=Registration.Status.APPROVED,
        )
        full = Section.objects.create(
            school_year=self.year,
            name='STEM-B',
            grade_level='Grade 12',
            program=self.program,
            capacity=1,
        )
        other_user = User.objects.create_user(email='ben@example.com', password='Strongpass1', role=User.Role.STUDENT)
        other = StudentProfile.objects.create(user=other_user, lrn='136000009922')
        StudentSection.objects.create(student=other, section=full, school_year=self.year)
        self.client.post('/api/admin/placements/', {'student': self.student.id, 'section': self.section.id}, format='json')
        blocked = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': full.id, 'transfer': True},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('capacity', blocked.data['detail'])
        forced = self.client.post(
            '/api/admin/placements/',
            {'student': self.student.id, 'section': full.id, 'transfer': True, 'override_capacity': True},
            format='json',
        )
        self.assertEqual(forced.status_code, 200, forced.data)
