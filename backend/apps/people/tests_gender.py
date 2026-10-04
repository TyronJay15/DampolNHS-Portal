from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.people.models import Registration
from apps.people.tests_access import make_programs
from apps.school.models import ProgramSubject, SchoolYear, Subject


def _client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


class RegistrationGenderTests(TestCase):
    PAYLOAD = {
        'first_name': 'Ana', 'last_name': 'Reyes', 'lrn': '136000000001', 'email': 'ana@x.com',
        'password': 'Strongpass1!', 'confirm_password': 'Strongpass1!', 'contact_number': '09171234567',
        'address': 'Dampol 1st, Pulilan, Bulacan', 'grade_level_enrollment': 'Grade 11', 'program': 'STEMC',
        'recaptcha_token': '',
    }

    def setUp(self):
        SchoolYear.objects.create(label='2026-2027', is_current=True)
        make_programs()

    def register(self, **extra):
        return _client().post('/api/register/', {**self.PAYLOAD, **extra}, format='json')

    def test_each_allowed_option_is_saved(self):
        for index, gender in enumerate(('female', 'male', 'prefer_not_to_say')):
            response = self.register(gender=gender, email=f'g{index}@x.com', lrn=f'13600000001{index}')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(StudentProfile.objects.get(user__email=f'g{index}@x.com').gender, gender)

    def test_gender_is_required_and_limited_to_the_options(self):
        missing = self.register()
        self.assertEqual(missing.status_code, 400)
        self.assertIn('gender', missing.data['errors'])
        made_up = self.register(gender='robot')
        self.assertEqual(made_up.status_code, 400)
        self.assertFalse(User.objects.filter(email='ana@x.com').exists())


class GenderEditTests(TestCase):
    def setUp(self):
        year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        programs = make_programs()
        self.student = User.objects.create_user(
            email='ana@x.com', password='Strongpass1', first_name='Ana', last_name='Reyes',
            role=User.Role.STUDENT, approval_status=User.ApprovalStatus.APPROVED,
        )
        self.profile = StudentProfile.objects.create(
            user=self.student, lrn='136000009921', contact_number='09171234567', address='Dampol 1st, Pulilan',
            grade_level='Grade 11',
        )
        Registration.objects.create(
            user=self.student, school_year=year, program=programs['STEMC'],
            grade_level_enrollment='Grade 11', status=Registration.Status.APPROVED,
        )
        self.admin = User.objects.create_user(email='admin@x.com', password='Strongpass1', role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(email='t@x.com', password='Strongpass1', role=User.Role.TEACHER)

    def test_student_edits_own_gender_and_it_is_audited(self):
        response = _client(self.student).patch('/api/students/me/', {'gender': 'male'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['gender'], 'male')
        log = AuditLog.objects.get(action='student_profile_updated')
        self.assertEqual(log.details['gender'], {'from': '', 'to': 'male'})

    def test_student_cannot_save_an_unknown_gender(self):
        response = _client(self.student).patch('/api/students/me/', {'gender': 'x'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.gender, '')

    def test_admin_corrects_gender_and_it_is_audited(self):
        url = f'/api/admin/accounts/{self.student.id}/gender/'
        response = _client(self.admin).patch(url, {'gender': 'prefer_not_to_say'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.gender, 'prefer_not_to_say')
        log = AuditLog.objects.get(action='student_gender_set')
        self.assertEqual((log.details['from'], log.details['to']), ('', 'prefer_not_to_say'))

    def test_only_the_admin_can_use_the_correction(self):
        url = f'/api/admin/accounts/{self.student.id}/gender/'
        for user in (self.student, self.teacher):
            self.assertEqual(_client(user).patch(url, {'gender': 'male'}, format='json').status_code, 403)
        self.assertEqual(_client(self.admin).patch(url, {'gender': 'robot'}, format='json').status_code, 400)
        missing = f'/api/admin/accounts/{self.admin.id}/gender/'
        self.assertEqual(_client(self.admin).patch(missing, {'gender': 'male'}, format='json').status_code, 404)

    def test_admin_registration_list_shows_gender(self):
        StudentProfile.objects.filter(pk=self.profile.pk).update(gender='female')
        rows = _client(self.admin).get('/api/admin/registrations/', {'status': 'approved'}).data['results']
        self.assertEqual(rows[0]['gender'], 'female')


class PublicProgramDetailsTests(TestCase):
    def setUp(self):
        self.programs = make_programs()
        subject = Subject.objects.create(code='gen-math', name='General Mathematics')
        ProgramSubject.objects.create(program=self.programs['STEMC'], subject=subject, kind='core', terms=[1])

    def test_programs_show_their_curriculum_without_internal_term_data(self):
        rows = {row['code']: row for row in _client().get('/api/programs/').data}
        self.assertTrue(rows['STEMC']['curriculum'])
        self.assertEqual(rows['STEMC']['subjects'], [{'id': rows['STEMC']['subjects'][0]['id'], 'code': 'gen-math', 'name': 'General Mathematics', 'kind': 'core'}])
