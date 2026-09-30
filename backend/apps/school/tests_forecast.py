from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.people.models import Registration
from apps.school.models import Curriculum, Program, SchoolYear


class Grade11ForecastTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        sshs = Curriculum.objects.get(code='strengthened-shs')
        k12 = Curriculum.objects.get(code='k12-shs')
        strands = {
            code: Program.objects.create(code=code, name=code, grade_level='Grade 12', curriculum=k12, sort_order=index)
            for index, code in enumerate(('STEM', 'ABM', 'HUMSS'), start=1)
        }

        def cluster(code, strand, order):
            return Program.objects.create(
                code=code,
                name=f'{code} Cluster',
                grade_level='Grade 11',
                curriculum=sshs,
                continues_to=strands[strand],
                sort_order=order,
            )

        self.stemc = cluster('STEMC', 'STEM', 13)
        self.be = cluster('BE', 'ABM', 12)
        cluster('ASH', 'HUMSS', 11)
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
        for index, program in enumerate((self.stemc, self.stemc, self.be)):
            user = User.objects.create_user(
                email=f'g11{index}@example.com',
                password='Strongpass1',
                first_name='Learner',
                last_name=str(index),
                role=User.Role.STUDENT,
                approval_status=User.ApprovalStatus.APPROVED,
            )
            Registration.objects.create(
                user=user,
                school_year=self.year,
                program=program,
                grade_level_enrollment='Grade 11',
                status=Registration.Status.APPROVED,
            )
        self.client = APIClient()

    def test_forecast_maps_clusters_to_strands(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/admin/forecast/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['school_year'], '2025-2026')
        self.assertEqual(response.data['projected_year'], '2026-2027')
        self.assertEqual(response.data['grade11_total'], 3)
        by_strand = {row['code']: row['count'] for row in response.data['strands']}
        self.assertEqual(by_strand['STEM'], 2)
        self.assertEqual(by_strand['ABM'], 1)
        self.assertEqual(by_strand['HUMSS'], 0)

    def test_teacher_cannot_read_forecast(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/admin/forecast/')
        self.assertEqual(response.status_code, 403)
