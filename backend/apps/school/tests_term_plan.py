from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import StudentProfile, User
from apps.audit.models import AuditLog
from apps.grading.models import Grade
from apps.grading.release import student_is_ready
from apps.grading.student_card import student_grade_card
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.models import Program, ProgramSubject, SchoolYear, Section, Subject, SubjectTermPlan, Term
from apps.school.term_plan import TermPlan, clean_terms, seed_year_plan


def _user(email, role, **extra):
    return User.objects.create_user(email=email, password='Strongpass1', first_name='Test', last_name='User', role=role, **extra)


class TermPlanBase(TestCase):
    """One STEM section with physics (Term 1 only by default) and research (every term)."""

    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.terms = [Term.objects.create(school_year=self.year, number=n, label=f'Term {n}') for n in (1, 2, 3)]
        self.program = Program.objects.create(code='STEM', name='STEM', grade_level='Grade 12')
        self.physics = Subject.objects.create(code='gen-phys-1', name='General Physics 1')
        self.research = Subject.objects.create(code='research', name='Research')
        ProgramSubject.objects.create(program=self.program, subject=self.physics, kind='specialized', terms=[1])
        ProgramSubject.objects.create(program=self.program, subject=self.research, kind='core', terms=[])
        seed_year_plan(self.year)
        self.section = Section.objects.create(
            school_year=self.year, name='STEM-A', grade_level='Grade 12', program=self.program
        )
        self.head = _user('head@dampol1nhs.edu.ph', User.Role.HEAD_TEACHER)
        self.teacher = _user('teacher@dampol1nhs.edu.ph', User.Role.TEACHER)
        student_user = _user('ana@example.com', User.Role.STUDENT)
        self.student = StudentProfile.objects.create(user=student_user, lrn='136000009921')
        StudentSection.objects.create(student=self.student, section=self.section, school_year=self.year)
        self.physics_duty = self._duty(self.physics)
        self.research_duty = self._duty(self.research)
        self.head_client = APIClient()
        self.head_client.force_authenticate(user=self.head)
        self.teacher_client = APIClient()
        self.teacher_client.force_authenticate(user=self.teacher)

    def _duty(self, subject):
        return TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            school_year=self.year,
            subject=subject,
            section=self.section,
        )

    def _grade(self, subject, term_number, status=Grade.Status.APPROVED):
        return Grade.objects.create(
            student=self.student,
            subject=subject,
            term=self.terms[term_number - 1],
            school_year=self.year,
            section=self.section,
            score=Decimal('90.00'),
            status=status,
            teacher=self.teacher,
        )

    def _save_plan(self, rows):
        return self.head_client.put(f'/api/school-years/{self.year.id}/term-plan/', {'rows': rows}, format='json')


class TermPlanRulesTests(TermPlanBase):
    def test_clean_terms_sorts_and_rejects_bad_values(self):
        self.assertEqual(clean_terms([3, '1', 3]), [1, 3])
        for bad in ([4], [0], ['x'], [True], 'all'):
            with self.assertRaises(ValueError):
                clean_terms(bad)

    def test_year_plan_copies_defaults_and_empty_means_every_term(self):
        plan = TermPlan(self.year.id)
        self.assertEqual(plan.terms_for(self.program.id, self.physics.id), [1])
        self.assertEqual(plan.terms_for(self.program.id, self.research.id), [1, 2, 3])
        self.assertEqual(SubjectTermPlan.objects.filter(school_year=self.year).count(), 2)

    def test_default_changes_do_not_rewrite_an_existing_year(self):
        ProgramSubject.objects.filter(subject=self.physics).update(terms=[2])
        self.assertEqual(TermPlan(self.year.id).terms_for(self.program.id, self.physics.id), [1])

    def test_subject_outside_the_program_list_runs_every_term(self):
        other = Subject.objects.create(code='pe', name='PE')
        self.assertEqual(TermPlan(self.year.id).terms_for(self.program.id, other.id), [1, 2, 3])

    def test_new_school_year_gets_a_plan(self):
        response = self.head_client.post('/api/school-years/', {'label': '2026-2027'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(SubjectTermPlan.objects.filter(school_year_id=response.data['id']).count(), 2)


class TermPlanApiTests(TermPlanBase):
    def test_head_teacher_reads_plan_with_graded_terms(self):
        self._grade(self.physics, 1)
        response = self.head_client.get(f'/api/school-years/{self.year.id}/term-plan/')
        self.assertEqual(response.status_code, 200)
        subjects = {row['code']: row for row in response.data['programs'][0]['subjects']}
        self.assertEqual(subjects['gen-phys-1']['terms'], [1])
        self.assertEqual(subjects['gen-phys-1']['graded_terms'], [1])
        self.assertEqual(subjects['research']['terms'], [1, 2, 3])

    def test_save_several_terms_counts_grades_left_outside_and_keeps_them(self):
        self._grade(self.physics, 1)
        response = self._save_plan([{'program': self.program.id, 'subject': self.physics.id, 'terms': [2, 3]}])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['saved'], 1)
        self.assertEqual(response.data['outside'], 1)
        self.assertEqual(TermPlan(self.year.id).terms_for(self.program.id, self.physics.id), [2, 3])
        self.assertEqual(Grade.objects.filter(subject=self.physics).count(), 1)
        log = AuditLog.objects.get(action='term_plan_saved')
        self.assertEqual(log.details['changed'][0]['to'], [2, 3])

    def test_unchanged_rows_are_not_logged(self):
        response = self._save_plan([{'program': self.program.id, 'subject': self.physics.id, 'terms': [1]}])
        self.assertEqual(response.data['saved'], 0)
        self.assertFalse(AuditLog.objects.filter(action='term_plan_saved').exists())

    def test_save_rejects_empty_terms_and_unknown_subjects(self):
        empty = self._save_plan([{'program': self.program.id, 'subject': self.physics.id, 'terms': []}])
        self.assertEqual(empty.status_code, 400)
        stray = Subject.objects.create(code='stray', name='Stray')
        unknown = self._save_plan([{'program': self.program.id, 'subject': stray.id, 'terms': [1]}])
        self.assertEqual(unknown.status_code, 400)

    def test_archived_year_is_read_only(self):
        from django.utils import timezone

        SchoolYear.objects.filter(pk=self.year.pk).update(archived_at=timezone.now(), is_current=False)
        response = self._save_plan([{'program': self.program.id, 'subject': self.physics.id, 'terms': [2]}])
        self.assertEqual(response.status_code, 400)

    def test_head_teacher_outside_grade_scope_cannot_save(self):
        TeacherAssignment.objects.create(
            teacher=self.head,
            assignment_type=TeacherAssignment.Type.HEAD_TEACHER,
            school_year=self.year,
            grade_level='Grade 11',
        )
        response = self._save_plan([{'program': self.program.id, 'subject': self.physics.id, 'terms': [2]}])
        self.assertEqual(response.status_code, 403)
        listed = self.head_client.get(f'/api/school-years/{self.year.id}/term-plan/')
        self.assertEqual(listed.data['programs'], [])

    def test_teacher_cannot_use_the_plan_endpoint(self):
        response = self.teacher_client.get(f'/api/school-years/{self.year.id}/term-plan/')
        self.assertEqual(response.status_code, 403)


class TermPlanEnforcementTests(TermPlanBase):
    def test_encoding_is_refused_in_an_unscheduled_term(self):
        payload = {'assignment': self.physics_duty.id, 'term': self.terms[1].id, 'student': self.student.id, 'score': 90}
        refused = self.teacher_client.post('/api/grades/encode/', payload, format='json')
        self.assertEqual(refused.status_code, 400)
        self.assertIn('not scheduled', refused.data['detail'])
        allowed = self.teacher_client.post('/api/grades/encode/', {**payload, 'term': self.terms[0].id}, format='json')
        self.assertEqual(allowed.status_code, 200, allowed.data)

    def test_submit_is_refused_in_an_unscheduled_term(self):
        response = self.teacher_client.post(
            '/api/grades/submit/', {'assignment': self.physics_duty.id, 'term': self.terms[1].id}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_class_view_marks_the_term_and_locks_rows(self):
        response = self.teacher_client.get(
            '/api/grades/class/', {'assignment': self.physics_duty.id, 'term': self.terms[1].id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['term']['scheduled'])
        self.assertEqual(response.data['assignment']['terms'], [1])
        self.assertFalse(response.data['students'][0]['editable'])

    def test_student_is_ready_counts_only_scheduled_subjects(self):
        self._grade(self.research, 2)
        self.assertTrue(student_is_ready(self.section, self.terms[1], self.student))
        self.assertFalse(student_is_ready(self.section, self.terms[0], self.student))

    def test_head_teacher_queue_skips_unscheduled_subjects(self):
        response = self.head_client.get('/api/grades/queues/', {'term': self.terms[1].id})
        subjects = {row['subject'] for row in response.data['groups']}
        self.assertEqual(subjects, {'Research'})

    def test_existing_grade_outside_the_plan_stays_on_the_card(self):
        self._grade(self.physics, 2, status=Grade.Status.RELEASED)
        card = student_grade_card(self.student)
        physics = next(row for row in card['subjects'] if row['id'] == self.physics.id)
        self.assertEqual(physics['terms'], [1])
        self.assertEqual([row['subject_id'] for row in card['grades']], [self.physics.id])


class TermPlanViewsTests(TermPlanBase):
    """What teachers, advisers, students and the admin see once the plan narrows a subject's terms."""

    def setUp(self):
        super().setUp()
        self.adviser = TeacherAssignment.objects.create(
            teacher=self.teacher,
            assignment_type=TeacherAssignment.Type.ADVISER,
            school_year=self.year,
            section=self.section,
        )

    def _duties(self):
        response = self.teacher_client.get('/api/teachers/assignments/')
        return {row['id']: row for row in response.data}

    def test_duties_list_only_the_terms_with_work(self):
        duties = self._duties()
        physics = duties[self.physics_duty.id]
        self.assertEqual(physics['terms'], [self.terms[0].id])
        self.assertEqual([row['term_id'] for row in physics['progress']['terms']], [self.terms[0].id])
        self.assertEqual(duties[self.adviser.id]['terms'], [term.id for term in self.terms])

    def test_a_term_that_already_holds_grades_stays_listed(self):
        self._grade(self.physics, 3)
        self.assertEqual(self._duties()[self.physics_duty.id]['terms'], [self.terms[0].id, self.terms[2].id])

    def test_adviser_term_disappears_when_no_subject_runs_in_it(self):
        self.research_duty.delete()
        self.assertEqual(self._duties()[self.adviser.id]['terms'], [self.terms[0].id])

    def test_adviser_shows_and_locks_all_terms_at_once(self):
        self._grade(self.physics, 1)
        self._grade(self.research, 2)
        body = {'assignment': self.adviser.id, 'term': 'all', 'student': self.student.id}
        shown = self.teacher_client.post('/api/grades/show/', body, format='json')
        self.assertEqual(shown.status_code, 200, shown.data)
        self.assertEqual(shown.data['shown'], 2)
        self.assertEqual(Grade.objects.filter(status=Grade.Status.RELEASED).count(), 2)
        hidden = self.teacher_client.post('/api/grades/hide/', body, format='json')
        self.assertEqual(hidden.data['hidden'], 2)
        self.assertFalse(Grade.objects.filter(status=Grade.Status.RELEASED).exists())

    def test_show_all_ready_covers_every_term(self):
        self._grade(self.physics, 1)
        self._grade(self.research, 3)
        response = self.teacher_client.post(
            '/api/grades/show-ready/', {'assignment': self.adviser.id, 'term': 'all'}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['shown'], 2)

    def test_show_all_with_nothing_approved_is_refused(self):
        body = {'assignment': self.adviser.id, 'term': 'all', 'student': self.student.id}
        self.assertEqual(self.teacher_client.post('/api/grades/show/', body, format='json').status_code, 400)

    def test_student_card_hides_terms_without_subjects(self):
        self.research_duty.delete()
        ProgramSubject.objects.filter(subject=self.research).delete()
        card = student_grade_card(self.student)
        self.assertEqual([row['number'] for row in card['terms']], [1])

    def test_admin_report_lists_only_that_terms_subjects_and_log_filters(self):
        admin = _user('admin@dampol1nhs.edu.ph', User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(user=admin)
        report = client.get('/api/grades/report/', {'school_year': self.year.id, 'term': self.terms[1].id})
        names = [row['name'] for row in report.data['sections'][0]['subjects']]
        self.assertEqual(names, ['Research'])

        payload = {'assignment': self.research_duty.id, 'term': self.terms[1].id, 'student': self.student.id, 'score': 88}
        self.teacher_client.post('/api/grades/encode/', payload, format='json')
        log = client.get('/api/grades/history/', {'school_year': self.year.id, 'term': self.terms[1].id})
        self.assertEqual(len(log.data), 1)
        empty = client.get('/api/grades/history/', {'term': self.terms[0].id})
        self.assertEqual(empty.data, [])
