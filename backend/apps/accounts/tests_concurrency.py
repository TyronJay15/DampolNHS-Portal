"""Simultaneous decisions on the same record (security plan N2): exactly one wins, with one audit entry and one
email or notification; the other is told it was already handled.

These tests commit for real (TransactionTestCase) so two database connections can race, and restore the seeded
reference data afterwards (serialized_rollback).
"""

import threading
from datetime import timedelta
from decimal import Decimal

from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.access import services as access
from apps.access.models import AccessRequest, AccessTag
from apps.accounts.models import MailOutbox, StudentProfile, User
from apps.audit.models import AuditLog
from apps.grading.corrections import CorrectionBlocked, review_correction
from apps.grading.models import CorrectionRequest, Grade, GradeHistory
from apps.grading.transitions import transition_grades
from apps.people.models import Registration
from apps.people.registrations import AlreadyReviewed, approve_registration
from apps.people.tests_access import make_programs
from apps.school.models import SchoolYear, Section, Subject, Term


def race(work, runners=2):
    """Run `work` in several threads that start together. Returns each result or the exception it raised."""
    barrier = threading.Barrier(runners)
    results = [None] * runners

    def run(index):
        close_old_connections()
        try:
            barrier.wait()
            results[index] = work()
        except Exception as exc:  # the loser's "already handled" is the point of the test
            results[index] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(runners)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def make_user(email, role):
    return User.objects.create_user(
        email=email,
        password='Strongpass1!',
        first_name='Ana',
        last_name='Cruz',
        role=role,
        approval_status=User.ApprovalStatus.APPROVED,
        account_status=User.AccountStatus.ACTIVE,
    )


@override_settings(MAIL_DELIVERY='background')
class SimultaneousDecisionTests(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.year = SchoolYear.objects.create(label='2026-2027', is_current=True)
        self.term = Term.objects.create(school_year=self.year, number=1, label='Term 1', status='active', is_current=True)
        self.programs = make_programs()
        self.admin = make_user('admin@x.com', User.Role.ADMIN)
        self.head = make_user('head@x.com', User.Role.HEAD_TEACHER)
        self.teacher = make_user('t@x.com', User.Role.TEACHER)
        self.student_user = make_user('ana@x.com', User.Role.STUDENT)
        self.student = StudentProfile.objects.create(user=self.student_user, lrn='136000000001', grade_level='Grade 11')

    def registration(self):
        self.student_user.approval_status = User.ApprovalStatus.PENDING
        self.student_user.save(update_fields=['approval_status'])
        return Registration.objects.create(
            user=self.student_user, school_year=self.year, program=self.programs['STEMC'], grade_level_enrollment='Grade 11'
        )

    def grades(self, count=3, status=Grade.Status.APPROVED):
        section = Section.objects.create(school_year=self.year, name='STEMC-A', grade_level='Grade 11', program=self.programs['STEMC'])
        rows = []
        for index in range(count):
            subject = Subject.objects.create(code=f'sub-{index}', name=f'Subject {index}')
            rows.append(
                Grade.objects.create(
                    student=self.student, subject=subject, term=self.term, school_year=self.year, section=section,
                    teacher=self.teacher, score=Decimal('90'), status=status,
                )
            )
        return rows

    def test_two_approvals_of_one_registration_approve_once(self):
        registration = self.registration()
        results = race(lambda: approve_registration(Registration.objects.get(pk=registration.pk), self.admin))
        self.assertEqual(sum(isinstance(row, dict) for row in results), 1, results)
        self.assertEqual(sum(isinstance(row, AlreadyReviewed) for row in results), 1, results)
        self.assertEqual(AuditLog.objects.filter(action='account_approved').count(), 1)
        self.assertEqual(MailOutbox.objects.filter(registration=registration).count(), 1)

    def test_two_reviews_of_one_correction_apply_once(self):
        grade = self.grades(1, status=Grade.Status.APPROVED)[0]
        correction = CorrectionRequest.objects.create(
            grade=grade, requested_by=self.teacher, current_score=Decimal('90'), proposed_score=Decimal('95'), reason='Typo'
        )
        results = race(
            lambda: review_correction(
                CorrectionRequest.objects.get(pk=correction.pk), CorrectionRequest.Status.APPROVED, '', self.head
            )
        )
        self.assertEqual(sum(isinstance(row, CorrectionRequest) for row in results), 1, results)
        self.assertEqual(sum(isinstance(row, CorrectionBlocked) for row in results), 1, results)
        self.assertEqual(AuditLog.objects.filter(action='correction_approved').count(), 1)
        self.assertEqual(GradeHistory.objects.filter(grade=grade, reason='Head teacher approved correction').count(), 1)

    def test_two_moves_of_the_same_grades_move_each_grade_once(self):
        rows = self.grades(3)
        results = race(
            lambda: transition_grades(
                grades=list(Grade.objects.filter(pk__in=[row.pk for row in rows])),
                to_status=Grade.Status.RELEASED,
                user=self.teacher,
                reason='Adviser showed report card',
                duty='adviser',
            )
        )
        self.assertEqual(sorted(results), [0, 3], results)
        self.assertEqual(GradeHistory.objects.filter(reason='Adviser showed report card').count(), 3)

    def test_two_decisions_on_one_access_request_decide_once(self):
        tag = AccessTag.objects.create(
            holder=self.head, activity='review_registrations', granted_by=self.admin, status=AccessTag.Status.ACTIVE
        )
        request = AccessRequest.objects.create(
            tag=tag, activity='review_registrations', requested_by=self.head, payload={}, summary='Approve 1 student',
            status=AccessRequest.Status.PENDING, expires_at=timezone.now() + timedelta(days=7),
        )
        results = race(lambda: access.decide(self.admin, AccessRequest.objects.get(pk=request.pk), False, 'Not now'))
        self.assertEqual(sum(isinstance(row, AccessRequest) for row in results), 1, results)
        self.assertEqual(sum(isinstance(row, Exception) for row in results), 1, results)
        self.assertEqual(AuditLog.objects.filter(action='access_request_declined').count(), 1)
