from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import StudentProfile, User
from apps.grading.models import Grade
from apps.grading.student_card import student_grade_card
from apps.people.models import StudentSection
from apps.school.models import Program, ProgramSubject, SchoolYear, Section, Subject, Term


class StudentCardAverageTests(TestCase):
    def setUp(self):
        self.year = SchoolYear.objects.create(label='2025-2026', is_current=True)
        self.program = Program.objects.create(code='STEM', name='STEM', sort_order=1)
        self.terms = [
            Term.objects.create(school_year=self.year, number=number, label=f'Term {number}')
            for number in (1, 2, 3)
        ]
        self.math = Subject.objects.create(code='math', name='Mathematics')
        self.science = Subject.objects.create(code='sci', name='Science')
        for subject in (self.math, self.science):
            ProgramSubject.objects.create(
                program=self.program,
                subject=subject,
                kind=ProgramSubject.Kind.CORE,
            )
        self.section = Section.objects.create(
            school_year=self.year,
            name='STEM-A',
            grade_level='Grade 11',
            program=self.program,
        )
        user = User.objects.create_user(
            email='ana@example.com',
            password='Strongpass1',
            first_name='Ana',
            last_name='Reyes',
            role=User.Role.STUDENT,
            approval_status=User.ApprovalStatus.APPROVED,
        )
        self.profile = StudentProfile.objects.create(
            user=user,
            lrn='136000009921',
            contact_number='09171234567',
            grade_level='Grade 11',
        )
        StudentSection.objects.create(
            student=self.profile,
            section=self.section,
            school_year=self.year,
        )

    def _grade(self, subject, term_number, score, status=Grade.Status.RELEASED):
        return Grade.objects.create(
            student=self.profile,
            subject=subject,
            term=self.terms[term_number - 1],
            school_year=self.year,
            score=Decimal(score),
            status=status,
            released_at=timezone.now() if status == Grade.Status.RELEASED else None,
        )

    def _subject_average(self, card, subject):
        return next(row for row in card['subject_averages'] if row['subject_id'] == subject.id)

    def _term_average(self, card, term_number):
        return next(row for row in card['term_averages'] if row['term_number'] == term_number)

    def test_empty_card_reports_no_averages(self):
        card = student_grade_card(self.profile)
        self.assertIsNone(self._subject_average(card, self.math)['average'])
        self.assertIsNone(self._term_average(card, 1)['average'])
        self.assertIsNone(card['overall_average']['average'])
        self.assertEqual(card['overall_average']['included'], 0)
        self.assertEqual(card['overall_average']['possible'], 6)

    def test_unreleased_scores_are_excluded(self):
        self._grade(self.math, 1, '90.00')
        self._grade(self.math, 2, '50.00', status=Grade.Status.SUBMITTED)
        self._grade(self.math, 3, '10.00', status=Grade.Status.DRAFT)

        row = self._subject_average(student_grade_card(self.profile), self.math)
        self.assertEqual(row['average'], '90.00')
        self.assertEqual(row['included'], 1)
        self.assertEqual(row['possible'], 3)

    def test_partial_coverage_averages_only_released_terms(self):
        self._grade(self.math, 1, '88.00')
        self._grade(self.math, 2, '91.00')

        card = student_grade_card(self.profile)
        subject = self._subject_average(card, self.math)
        self.assertEqual(subject['average'], '89.50')
        self.assertEqual(subject['included'], 2)
        self.assertEqual(subject['possible'], 3)

        term = self._term_average(card, 1)
        self.assertEqual(term['average'], '88.00')
        self.assertEqual(term['included'], 1)
        self.assertEqual(term['possible'], 2)

        self.assertIsNone(self._subject_average(card, self.science)['average'])
        self.assertIsNone(self._term_average(card, 3)['average'])

    def test_term_and_overall_averages_span_subjects(self):
        self._grade(self.math, 1, '90.00')
        self._grade(self.science, 1, '80.00')
        self._grade(self.math, 2, '95.00')

        card = student_grade_card(self.profile)
        self.assertEqual(self._term_average(card, 1)['average'], '85.00')
        self.assertEqual(self._term_average(card, 2)['average'], '95.00')
        self.assertEqual(card['overall_average']['average'], '88.33')
        self.assertEqual(card['overall_average']['included'], 3)
        self.assertEqual(card['overall_average']['possible'], 6)

    def test_averages_round_half_up(self):
        self._grade(self.math, 1, '89.00')
        self._grade(self.math, 2, '90.01')

        row = self._subject_average(student_grade_card(self.profile), self.math)
        self.assertEqual(row['average'], '89.51')

    def test_one_term_subject_possible_is_one(self):
        elective = Subject.objects.create(code='pe', name='Physical Education')
        ProgramSubject.objects.create(
            program=self.program,
            subject=elective,
            kind=ProgramSubject.Kind.ELECTIVE,
            term=2,
        )
        self._grade(elective, 2, '92.00')

        card = student_grade_card(self.profile)
        row = self._subject_average(card, elective)
        self.assertEqual(row['average'], '92.00')
        self.assertEqual(row['included'], 1)
        self.assertEqual(row['possible'], 1)
        self.assertEqual(self._term_average(card, 1)['possible'], 2)
        self.assertEqual(self._term_average(card, 2)['possible'], 3)
        self.assertEqual(card['overall_average']['possible'], 7)

    def test_overall_is_mean_of_scores_not_averages(self):
        self._grade(self.math, 1, '90.00')
        self._grade(self.math, 2, '90.00')
        self._grade(self.math, 3, '90.00')
        self._grade(self.science, 1, '60.00')

        card = student_grade_card(self.profile)
        self.assertEqual(self._subject_average(card, self.math)['average'], '90.00')
        self.assertEqual(self._subject_average(card, self.science)['average'], '60.00')
        self.assertEqual(card['overall_average']['average'], '82.50')
        self.assertEqual(card['overall_average']['included'], 4)
