from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.people.scope import head_grade_scope
from apps.school.models import Curriculum, Program, SchoolYear, SchoolYearCurriculum, Section, Subject, Term


def make_programs():
    k12 = Curriculum.objects.get(code='k12-shs')
    sshs = Curriculum.objects.get(code='strengthened-shs')
    return {
        'ASH': Program.objects.create(code='ASH', name='Arts Cluster', grade_level='Grade 11', curriculum=sshs, description='Arts text'),
        'STEMC': Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11', curriculum=sshs, description='STEMC text'),
        'STEM': Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12', curriculum=k12, description='STEM text'),
        'HUMSS': Program.objects.create(code='HUMSS', name='HUMSS', grade_level='Grade 12', curriculum=k12, description='HUMSS text'),
    }


class ProgramDescriptionTests(TestCase):
    def setUp(self):
        self.programs = make_programs()
        self.admin = User.objects.create_user(email='admin@x.com', password='Strongpass1', role=User.Role.ADMIN)

    def test_every_program_keeps_its_own_description(self):
        rows = {row['code']: row['description'] for row in APIClient().get('/api/programs/').data}
        self.assertEqual(rows, {'ASH': 'Arts text', 'STEMC': 'STEMC text', 'STEM': 'STEM text', 'HUMSS': 'HUMSS text'})

    def test_editing_one_program_leaves_the_others_alone(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.patch(f"/api/admin/programs/{self.programs['STEM'].pk}/", {'description': 'New STEM text'}, format='json')
        self.assertEqual(response.status_code, 200)
        rows = {row['code']: row['description'] for row in APIClient().get('/api/programs/').data}
        self.assertEqual(rows['STEM'], 'New STEM text')
        self.assertEqual((rows['STEMC'], rows['HUMSS'], rows['ASH']), ('STEMC text', 'HUMSS text', 'Arts text'))
        self.assertEqual(Program.objects.count(), 4)


class EnrollmentGradeProgramTests(TestCase):
    PAYLOAD = {
        'first_name': 'Ana', 'last_name': 'Reyes', 'lrn': '136000000001', 'email': 'ana@x.com',
        'password': 'Strongpass1!', 'confirm_password': 'Strongpass1!', 'contact_number': '09171234567',
        'address': 'Dampol 1st, Pulilan, Bulacan', 'gender': 'female', 'recaptcha_token': '',
    }

    def setUp(self):
        SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.programs = make_programs()

    def codes(self, grade):
        return sorted(row['code'] for row in APIClient().get('/api/programs/', {'grade_level': grade}).data)

    def register(self, grade, program, **extra):
        return APIClient().post('/api/register/', {**self.PAYLOAD, 'grade_level_enrollment': grade, 'program': program, **extra}, format='json')

    def test_programs_are_filtered_by_grade_level_on_the_server(self):
        self.assertEqual(self.codes('Grade 11'), ['ASH', 'STEMC'])
        self.assertEqual(self.codes('Grade 12'), ['HUMSS', 'STEM'])
        self.assertEqual(self.codes('Grade 10'), [])
        self.assertEqual(len(APIClient().get('/api/programs/').data), 4)

    def test_inactive_program_is_not_offered(self):
        Program.objects.filter(code='ASH').update(is_active=False)
        self.assertEqual(self.codes('Grade 11'), ['STEMC'])

    def test_valid_enrollment_works(self):
        for grade, program, email, lrn in (('Grade 11', 'STEMC', 'a@x.com', '136000000011'), ('Grade 12', 'STEM', 'b@x.com', '136000000012')):
            response = self.register(grade, program, email=email, lrn=lrn)
            self.assertEqual(response.status_code, 201, response.data)
            row = Registration.objects.get(user__email=email)
            self.assertEqual((row.grade_level_enrollment, row.program.code), (grade, program))

    def test_mismatched_grade_and_program_is_rejected(self):
        response = self.register('Grade 11', 'STEM')
        self.assertEqual(response.status_code, 400)
        self.assertIn('program', response.data['errors'])
        self.assertEqual(self.register('Grade 12', 'ASH').status_code, 400)
        self.assertFalse(User.objects.filter(email='ana@x.com').exists())
        self.assertEqual(Registration.objects.count(), 0)

    def test_program_not_offered_in_the_years_curriculum_is_rejected(self):
        k12 = Curriculum.objects.get(code='k12-shs')
        sshs = Curriculum.objects.get(code='strengthened-shs')
        SchoolYearCurriculum.objects.create(school_year=SchoolYear.objects.get(is_current=True), grade_level='Grade 11', curriculum=sshs)
        Program.objects.filter(code='STEMC').update(curriculum=k12)
        self.assertEqual(self.register('Grade 11', 'STEMC').status_code, 400)
        self.assertEqual(self.codes('Grade 11'), ['ASH'])


class HeadTeacherAccessTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        self.programs = make_programs()
        self.g11 = Section.objects.create(school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC'])
        self.g12 = Section.objects.create(school_year=self.year, name='STEM-A', grade_level='Grade 12', program=self.programs['STEM'])
        make = lambda email, role: User.objects.create_user(email=email, password='Strongpass1', first_name=email[:3], role=role)  # noqa: E731
        self.admin = make('admin@x.com', User.Role.ADMIN)
        self.head_all = make('hall@x.com', User.Role.HEAD_TEACHER)
        self.head11 = make('h11@x.com', User.Role.HEAD_TEACHER)
        self.head12 = make('h12@x.com', User.Role.HEAD_TEACHER)
        self.teacher = make('teach@x.com', User.Role.TEACHER)
        for head, level in ((self.head11, 'Grade 11'), (self.head12, 'Grade 12')):
            TeacherAssignment.objects.create(teacher=head, assignment_type='head_teacher', school_year=self.year, grade_level=level)

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_head_teacher_is_not_an_admin(self):
        for url in ('/api/admin/registrations/', '/api/admin/programs/', '/api/admin/forecast/', '/api/admin/staff/', '/api/admin/accounts/1/deactivate/'):
            method = 'post' if url.endswith('deactivate/') else 'get'
            self.assertEqual(getattr(self.as_user(self.head_all), method)(url).status_code, 403, url)
        self.assertEqual(self.as_user(self.admin).get('/api/sections/').status_code, 403)
        self.assertEqual(self.as_user(self.teacher).get('/api/sections/').status_code, 403)

    def test_several_head_teachers_each_see_only_their_grade_level(self):
        self.assertEqual(head_grade_scope(self.head11), {'Grade 11'})
        self.assertEqual(head_grade_scope(self.head12), {'Grade 12'})
        self.assertIsNone(head_grade_scope(self.head_all))
        names = lambda user: sorted(row['name'] for row in self.as_user(user).get('/api/sections/').data)  # noqa: E731
        self.assertEqual(names(self.head11), ['STEMC-A'])
        self.assertEqual(names(self.head12), ['STEM-A'])
        self.assertEqual(names(self.head_all), ['STEM-A', 'STEMC-A'])

    def test_section_actions_outside_scope_are_refused(self):
        self.assertEqual(self.as_user(self.head11).get(f'/api/sections/{self.g12.pk}/').status_code, 404)
        self.assertEqual(self.as_user(self.head11).get(f'/api/sections/{self.g12.pk}/detail/').status_code, 403)
        self.assertEqual(self.as_user(self.head12).get(f'/api/sections/{self.g12.pk}/detail/').status_code, 200)
        created = self.as_user(self.head11).post(
            '/api/sections/', {'name': 'X', 'grade_level': 'Grade 12', 'program': self.programs['STEM'].pk, 'school_year': self.year.pk}, format='json'
        )
        self.assertEqual(created.status_code, 403)

    def test_placement_and_assignment_outside_scope_are_refused(self):
        user = User.objects.create_user(email='s@x.com', password='Strongpass1', role=User.Role.STUDENT, approval_status='approved')
        profile = StudentProfile.objects.create(user=user, lrn='136000000099', grade_level='Grade 12')
        Registration.objects.create(user=user, school_year=self.year, program=self.programs['STEM'], grade_level_enrollment='Grade 12', status='approved')
        denied = self.as_user(self.head11).post('/api/admin/placements/', {'student': profile.pk, 'section': self.g12.pk}, format='json')
        self.assertEqual(denied.status_code, 403)
        allowed = self.as_user(self.head12).post('/api/admin/placements/', {'student': profile.pk, 'section': self.g12.pk}, format='json')
        self.assertEqual(allowed.status_code, 200, allowed.data)
        self.assertNotIn(profile.pk, [row['student_id'] for row in self.as_user(self.head11).get('/api/admin/placements/').data])
        subject = Subject.objects.create(code='gen-math', name='General Mathematics')
        denied = self.as_user(self.head11).post(
            '/api/admin/assignments/', {'teacher': self.teacher.pk, 'type': 'adviser', 'section': self.g12.pk}, format='json'
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(subject.pk)

    def test_approvals_and_corrections_outside_scope_are_ignored_or_refused(self):
        user = User.objects.create_user(email='s2@x.com', password='Strongpass1', role=User.Role.STUDENT, approval_status='approved')
        profile = StudentProfile.objects.create(user=user, lrn='136000000098', grade_level='Grade 12')
        subject = Subject.objects.create(code='gen-math', name='General Mathematics')
        StudentSection.objects.create(student=profile, section=self.g12, school_year=self.year)
        grade = Grade.objects.create(
            student=profile, subject=subject, term=self.term, school_year=self.year, section=self.g12,
            teacher=self.teacher, score=Decimal('90'), status=Grade.Status.SUBMITTED,
        )
        none = self.as_user(self.head11).post('/api/grades/approve/all/', {'term': self.term.pk}, format='json')
        self.assertEqual(none.data['approved'], 0)
        grade.refresh_from_db()
        self.assertEqual(grade.status, Grade.Status.SUBMITTED)
        denied = self.as_user(self.head11).post('/api/grades/return/', {'term': self.term.pk, 'section': self.g12.pk, 'subject': subject.pk}, format='json')
        self.assertEqual(denied.status_code, 403)
        done = self.as_user(self.head12).post('/api/grades/approve/all/', {'term': self.term.pk}, format='json')
        self.assertEqual(done.data['approved'], 1)
