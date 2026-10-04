from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, SchoolYear, Section, Subject, Term


class PrintFixture(TestCase):
    """Two sections, a subject teacher per subject, an adviser, a head teacher and released grades."""

    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1')
        program = Program.objects.create(code='STEMC', name='STEM Cluster', grade_level='Grade 11')
        self.section = Section.objects.create(school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=program)
        self.other_section = Section.objects.create(school_year=self.year, name='STEMC-B', grade_level='Grade 11', program=program)
        self.math = Subject.objects.create(code='gen-math', name='General Mathematics')
        self.sci = Subject.objects.create(code='gen-sci', name='General Science')
        self.teacher = self.user('math@x.com', User.Role.TEACHER, 'Math', 'Teacher')
        self.sci_teacher = self.user('sci@x.com', User.Role.TEACHER, 'Sci', 'Teacher')
        self.adviser = self.user('adv@x.com', User.Role.TEACHER, 'Ad', 'Viser')
        self.stranger = self.user('other@x.com', User.Role.TEACHER, 'Some', 'Other')
        self.head = self.user('head@x.com', User.Role.HEAD_TEACHER, 'Head', 'One')
        self.admin = self.user('admin@x.com', User.Role.ADMIN, 'Ad', 'Min')
        self.ana, self.ana_profile = self.student('ana@x.com', 'Ana', '136000000001', self.section)
        self.ben, self.ben_profile = self.student('ben@x.com', 'Ben', '136000000002', self.other_section)
        for subject, teacher in ((self.math, self.teacher), (self.sci, self.sci_teacher)):
            TeacherAssignment.objects.create(
                teacher=teacher, assignment_type='subject_teacher', school_year=self.year, section=self.section, subject=subject
            )
        TeacherAssignment.objects.create(teacher=self.adviser, assignment_type='adviser', school_year=self.year, section=self.section)
        self.grade(self.ana_profile, self.math, '90', Grade.Status.RELEASED, self.teacher)
        self.grade(self.ana_profile, self.sci, '70', Grade.Status.RELEASED, self.sci_teacher)
        self.grade(self.ana_profile, self.math, '99', Grade.Status.APPROVED, self.teacher, term=2)
        self.grade(self.ben_profile, self.math, '88', Grade.Status.RELEASED, self.teacher)

    def user(self, email, role, first, last):
        return User.objects.create_user(
            email=email, password='Strongpass1', first_name=first, last_name=last, role=role, approval_status='approved'
        )

    def student(self, email, name, lrn, section):
        user = self.user(email, User.Role.STUDENT, name, 'Reyes')
        profile = StudentProfile.objects.create(user=user, lrn=lrn, grade_level='Grade 11')
        StudentSection.objects.create(student=profile, section=section, school_year=self.year)
        return user, profile

    def grade(self, profile, subject, score, status, teacher, term=1):
        term_row = self.term if term == 1 else Term.objects.get_or_create(
            school_year=self.year, number=term, defaults={'label': f'Term {term}'}
        )[0]
        return Grade.objects.create(
            student=profile,
            subject=subject,
            term=term_row,
            school_year=self.year,
            section=profile.section_assignments.first().section,
            teacher=teacher,
            score=Decimal(score),
            status=status,
        )

    def get(self, user, **params):
        client = APIClient()
        client.force_authenticate(user=user)
        query = '&'.join(f'{key}={value}' for key, value in params.items())
        return client.get(f'/api/grades/print/?{query}')


class GradePrintTests(PrintFixture):
    def test_student_prints_own_released_grades_with_school_details(self):
        response = self.get(self.ana)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['student']['lrn'], '136000000001')
        self.assertEqual((data['student']['grade_level'], data['student']['program'], data['school_year']), ('Grade 11', 'STEMC', '2025-2026'))
        self.assertEqual(
            {(row['subject'], row['grade'], row['teacher'], row['remarks']) for row in data['rows']},
            {
                ('General Mathematics', '90.00', 'Math Teacher', 'Passed'),
                ('General Science', '70.00', 'Sci Teacher', 'Did not meet the passing grade'),
            },
        )
        self.assertNotIn('99.00', [row['grade'] for row in data['rows']])
        self.assertTrue(data['school'] and data['generated_at'])

    def test_student_cannot_print_another_students_grades(self):
        response = self.get(self.ana, student=self.ben_profile.pk)
        self.assertEqual(response.data['student']['lrn'], '136000000001')
        self.assertEqual([row['grade'] for row in response.data['rows']], ['90.00', '70.00'])

    def test_term_filter(self):
        response = self.get(self.ana, term=self.term.pk)
        self.assertEqual({row['term'] for row in response.data['rows']}, {'Term 1'})

    def test_adviser_sees_all_subjects_and_approved_grades(self):
        response = self.get(self.adviser, student=self.ana_profile.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn('99.00', [row['grade'] for row in response.data['rows']])
        self.assertEqual(len(response.data['rows']), 3)

    def test_subject_teacher_only_gets_their_own_subject(self):
        response = self.get(self.sci_teacher, student=self.ana_profile.pk)
        self.assertEqual({row['subject'] for row in response.data['rows']}, {'General Science'})

    def test_unassigned_teacher_is_refused(self):
        self.assertEqual(self.get(self.stranger, student=self.ana_profile.pk).status_code, 403)
        self.assertEqual(self.get(self.teacher, student=self.ben_profile.pk).status_code, 403)

    def test_head_teacher_and_admin(self):
        self.assertEqual(self.get(self.head, student=self.ana_profile.pk).status_code, 200)
        self.assertEqual(self.get(self.admin, student=self.ben_profile.pk).status_code, 200)

    def test_head_teacher_limited_to_assigned_grade_level(self):
        TeacherAssignment.objects.create(
            teacher=self.head, assignment_type='head_teacher', school_year=self.year, grade_level='Grade 12'
        )
        self.assertEqual(self.get(self.head, student=self.ana_profile.pk).status_code, 403)

    def test_missing_student_and_anonymous(self):
        self.assertEqual(self.get(self.admin, student=9999).status_code, 404)
        self.assertEqual(APIClient().get('/api/grades/print/').status_code, 401)

    def test_printing_changes_nothing(self):
        columns = ('pk', 'score', 'status', 'updated_at')
        before = list(Grade.objects.order_by('pk').values_list(*columns))
        self.get(self.adviser, student=self.ana_profile.pk)
        self.get(self.ana)
        self.assertEqual(before, list(Grade.objects.order_by('pk').values_list(*columns)))


class GradeRecordsPrintTests(PrintFixture):
    """The staff export behind My Account → ⋯ → Print my grade records."""

    def records(self, user, **params):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get('/api/grades/print/records/', params)

    def test_teacher_gets_a_sheet_per_class_with_only_their_subject(self):
        response = self.records(self.teacher)
        self.assertEqual(response.status_code, 200)
        titles = [group['title'] for group in response.data['groups']]
        self.assertEqual(len(titles), 1)
        self.assertIn('General Mathematics', titles[0])
        grades = sorted(row['grade'] for row in response.data['groups'][0]['rows'])
        self.assertEqual(grades, ['90.00', '99.00'])
        self.assertEqual(response.data['term'], 'All terms')

    def test_teacher_term_filter(self):
        response = self.records(self.teacher, term=self.term.pk)
        self.assertEqual([row['grade'] for row in response.data['groups'][0]['rows']], ['90.00'])

    def test_head_teacher_gets_their_grade_decisions(self):
        from apps.grading.history import HEAD_TEACHER, write_history

        grade = Grade.objects.get(student=self.ana_profile, subject=self.sci)
        write_history(
            grade=grade, from_status='submitted', to_status='approved', previous_score=None,
            new_score=None, user=self.head, reason='Head teacher approved grades', duty=HEAD_TEACHER,
        )
        rows = self.records(self.head).data['groups'][0]['rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['change'], 'submitted → approved')

    def test_students_and_admin_have_no_records_export(self):
        self.assertEqual(self.records(self.ana).status_code, 403)
        self.assertEqual(self.records(self.admin).status_code, 403)

    def test_student_print_lists_the_years_terms(self):
        labels = [row['label'] for row in self.get(self.ana).data['terms']]
        self.assertIn('Term 1', labels)
