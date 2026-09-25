from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit import services as audit


class AuditLogApiTests(TestCase):
    def setUp(self):
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
        audit.record(
            user=self.admin,
            action='account_approved',
            summary='Approved student account ana@example.com',
            target_type='User',
            target_id=1,
        )
        self.client = APIClient()

    def test_admin_reads_audit_log(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/audit-logs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['action'], 'account_approved')
        self.assertEqual(response.data[0]['actor'], 'admin@dampol1nhs.edu.ph')

    def test_teacher_cannot_read_audit_log(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/audit-logs/')
        self.assertEqual(response.status_code, 403)
