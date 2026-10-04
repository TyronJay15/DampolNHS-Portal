from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.school.models import Program, ProgramSubject, Subject
from apps.school.offerings import seed_programs, sync_subject_catalog


class ProgramCmsTests(TestCase):
    def setUp(self):
        seed_programs()
        sync_subject_catalog()
        self.ash = Program.objects.get(code='ASH')
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
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_edit_program_copy(self):
        response = self.client.patch(
            f'/api/admin/programs/{self.ash.id}/',
            {
                'name': 'Arts and Social Humanities',
                'summary': 'Updated cluster summary.',
                'track': 'Academic Cluster',
                'pathways': ['Education', 'Psychology'],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.ash.refresh_from_db()
        self.assertEqual(self.ash.name, 'Arts and Social Humanities')
        self.assertEqual(self.ash.track, 'Academic Cluster')
        self.assertEqual(self.ash.pathways, ['Education', 'Psychology'])

        public = self.client.get('/api/programs/')
        ash = next(row for row in public.data if row['code'] == 'ASH')
        self.assertEqual(ash['name'], 'Arts and Social Humanities')
        self.assertEqual(ash['track'], 'Academic Cluster')
        self.assertEqual(ash['pathways'], ['Education', 'Psychology'])

    def test_admin_can_replace_program_subjects(self):
        comm = Subject.objects.get(code='eff-comm')
        bio = Subject.objects.get(code='bio-1')
        response = self.client.patch(
            f'/api/admin/programs/{self.ash.id}/',
            {
                'subjects': [
                    {'subject_id': comm.id, 'kind': 'core', 'terms': [1]},
                    {'subject_id': bio.id, 'kind': 'specialized', 'terms': [2, 3]},
                ]
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        codes = set(
            ProgramSubject.objects.filter(program=self.ash).values_list('subject__code', flat=True)
        )
        self.assertEqual(codes, {'eff-comm', 'bio-1'})
        self.assertEqual(ProgramSubject.objects.get(program=self.ash, subject=bio).terms, [2, 3])
        names = [row['name'] for row in response.data['subjects']]
        self.assertIn(comm.name, names)
        self.assertIn(bio.name, names)

    def test_setup_school_keeps_cms_edits(self):
        self.ash.name = 'Edited Arts cluster'
        self.ash.summary = 'Kept by CMS'
        self.ash.save(update_fields=['name', 'summary'])
        call_command('setup_school', password='changeme123')
        self.ash.refresh_from_db()
        self.assertEqual(self.ash.name, 'Edited Arts cluster')
        self.assertEqual(self.ash.summary, 'Kept by CMS')

    def test_staff_cannot_edit_programs(self):
        self.client.force_authenticate(user=self.head)
        response = self.client.patch(
            f'/api/admin/programs/{self.ash.id}/',
            {'name': 'Nope'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_add_subject_and_program(self):
        created = self.client.post(
            '/api/admin/subjects/',
            {'code': 'new-core', 'name': 'New Core Subject'},
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)
        program = self.client.post(
            '/api/admin/programs/',
            {
                'code': 'arts2',
                'name': 'New Arts Cluster',
                'grade_level': 'Grade 11',
                'track': 'Academic Cluster',
                'summary': 'Added from CMS.',
                'subjects': [{'subject_id': created.data['id'], 'kind': 'core', 'terms': [1]}],
            },
            format='json',
        )
        self.assertEqual(program.status_code, 201, program.data)
        self.assertEqual(program.data['code'], 'ARTS2')
        self.assertEqual(program.data['subjects'][0]['code'], 'new-core')
