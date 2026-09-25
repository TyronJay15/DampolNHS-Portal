from django.core import mail
from rest_framework.test import APITestCase

from apps.accounts.models import StudentProfile, User
from apps.notifications.models import Notification
from apps.people.models import Registration
from apps.school.models import Program, SchoolYear


class AccountLockTests(APITestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='ASH', name='Arts cluster', grade_level='Grade 11')
        self.admin = User.objects.create_user(
            email='admin@school.test',
            password='admin-pass',
            first_name='Ada',
            last_name='Min',
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def _student(self, email, lrn, approval=User.ApprovalStatus.APPROVED, reg_status=Registration.Status.APPROVED):
        user = User.objects.create_user(
            email=email,
            password='Studentpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
            approval_status=approval,
            account_status=User.AccountStatus.ACTIVE,
        )
        StudentProfile.objects.create(user=user, lrn=lrn)
        Registration.objects.create(
            user=user,
            school_year=self.year,
            program=self.program,
            grade_level_enrollment='Grade 11',
            status=reg_status,
        )
        return user

    def test_deactivate_approved_student_blocks_login_and_emails(self):
        student = self._student('ana@school.test', '136000009921')
        response = self.client.post(f'/api/admin/accounts/{student.id}/deactivate/', {'reason': 'Left school.'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        student.refresh_from_db()
        self.assertEqual(student.account_status, User.AccountStatus.ARCHIVED)
        self.assertEqual(Registration.objects.get(user=student).status, Registration.Status.APPROVED)
        self.assertTrue(Notification.objects.filter(user=student, title='Account archived').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('deactivated', mail.outbox[0].subject.lower())

        self.client.force_authenticate(user=None)
        denied = self.client.post(
            '/api/auth/login/',
            {'identifier': '136000009921', 'password': 'Studentpass1'},
            format='json',
        )
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.data.get('code'), 'account_deactivated')

    def test_deactivate_pending_also_rejects_registration(self):
        student = self._student(
            'pending@school.test',
            '136000009922',
            approval=User.ApprovalStatus.PENDING,
            reg_status=Registration.Status.PENDING,
        )
        response = self.client.post(f'/api/admin/accounts/{student.id}/deactivate/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['rejected_pending'])
        student.refresh_from_db()
        registration = Registration.objects.get(user=student)
        self.assertEqual(student.account_status, User.AccountStatus.ARCHIVED)
        self.assertEqual(student.approval_status, User.ApprovalStatus.REJECTED)
        self.assertEqual(registration.status, Registration.Status.REJECTED)

    def test_reactivate_clears_password_and_sends_code(self):
        teacher = User.objects.create_user(
            email='teacher@school.test',
            password='Teacherpass1',
            first_name='Liza',
            last_name='Cruz',
            role=User.Role.TEACHER,
            account_status=User.AccountStatus.SUSPENDED,
        )
        response = self.client.post(f'/api/admin/accounts/{teacher.id}/reactivate/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        teacher.refresh_from_db()
        self.assertEqual(teacher.account_status, User.AccountStatus.PENDING_ACTIVATION)
        self.assertFalse(teacher.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('activation', mail.outbox[0].subject.lower())

    def test_cannot_deactivate_self_or_last_admin(self):
        self.assertEqual(
            self.client.post(f'/api/admin/accounts/{self.admin.id}/deactivate/', {}, format='json').status_code,
            400,
        )
        other = User.objects.create_user(
            email='second@school.test',
            password='Adminpass1',
            first_name='Bea',
            last_name='Cruz',
            role=User.Role.ADMIN,
        )
        other.account_status = User.AccountStatus.SUSPENDED
        other.save(update_fields=['account_status'])
        self.assertEqual(
            self.client.post(f'/api/admin/accounts/{self.admin.id}/deactivate/', {}, format='json').status_code,
            400,
        )

    def test_remove_anonymizes_archived_account(self):
        student = self._student('gone@school.test', '136000009923')
        self.client.post(f'/api/admin/accounts/{student.id}/deactivate/', {}, format='json')
        removed = self.client.post(f'/api/admin/accounts/{student.id}/remove/', {}, format='json')
        self.assertEqual(removed.status_code, 200, removed.data)
        student.refresh_from_db()
        self.assertEqual(student.account_status, User.AccountStatus.REMOVED)
        self.assertTrue(student.email.endswith('@archived.invalid'))
        self.assertEqual(student.student_profile.lrn, f'REMOVED-{student.id}')
        refused = self.client.post(f'/api/admin/accounts/{student.id}/reactivate/', {}, format='json')
        self.assertEqual(refused.status_code, 400)

    def test_cannot_remove_active_account(self):
        student = self._student('keep@school.test', '136000009924')
        response = self.client.post(f'/api/admin/accounts/{student.id}/remove/', {}, format='json')
        self.assertEqual(response.status_code, 400)
