from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.people.models import Registration
from apps.school.models import Program, SchoolYear


class StudentMePermissionTests(TestCase):
    def test_student_me_requires_login(self):
        client = APIClient()
        response = client.get('/api/students/me/')
        self.assertEqual(response.status_code, 401)

    def test_admin_cannot_use_student_me(self):
        admin = User.objects.create_user(
            email='admin@dampol1nhs.edu.ph',
            password='changeme123',
            first_name='School',
            last_name='Admin',
            role=User.Role.ADMIN,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/students/me/')
        self.assertEqual(response.status_code, 403)


class StudentProfileUpdateTests(TestCase):
    def setUp(self):
        year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        program = Program.objects.create(code='ICTP', name='ICT Cluster', grade_level='Grade 11')
        self.user = User.objects.create_user(
            email='ana@school.test',
            password='Studentpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.APPROVED,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            lrn='136000009921',
            contact_number='09171234567',
            address='Dampol 1st, Pulilan',
            guardian_name='Lina Reyes',
            guardian_contact='09180000000',
            grade_level='Grade 11',
        )
        Registration.objects.create(
            user=self.user,
            school_year=year,
            program=program,
            grade_level_enrollment='Grade 11',
            status=Registration.Status.APPROVED,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_includes_contact_fields(self):
        response = self.client.get('/api/students/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['contact_number'], '09171234567')
        self.assertEqual(response.data['address'], 'Dampol 1st, Pulilan')
        self.assertEqual(response.data['guardian_name'], 'Lina Reyes')
        self.assertEqual(response.data['lrn'], '136000009921')

    def test_student_can_update_contact_fields(self):
        response = self.client.patch(
            '/api/students/me/',
            {
                'contact_number': '09179876543',
                'address': 'Sto. Cristo, Pulilan, Bulacan',
                'guardian_name': 'Mario Reyes',
                'guardian_contact': '09181112222',
                'lrn': '136000000000',
                'first_name': 'Changed',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['contact_number'], '09179876543')
        self.assertEqual(response.data['address'], 'Sto. Cristo, Pulilan, Bulacan')
        self.assertEqual(response.data['guardian_name'], 'Mario Reyes')
        self.assertEqual(response.data['lrn'], '136000009921')
        self.assertEqual(response.data['first_name'], 'Ana')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contact_number, '09179876543')
        self.assertEqual(self.profile.lrn, '136000009921')
        log = AuditLog.objects.filter(action='student_profile_updated').first()
        self.assertIsNotNone(log)
        self.assertIn('contact_number', log.details['changed'])

    def test_invalid_contact_is_rejected(self):
        response = self.client.patch(
            '/api/students/me/',
            {'contact_number': '12345', 'address': 'Dampol 1st, Pulilan'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contact_number, '09171234567')
