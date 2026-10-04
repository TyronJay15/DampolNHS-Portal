"""Giving a teacher a duty, shared by the Head Teacher's screen and approved access requests."""

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import User
from apps.audit import services as audit
from apps.audit.catalog import ASSIGNMENTS
from apps.notifications.services import notify
from apps.people.models import TeacherAssignment
from apps.people.placement import current_year
from apps.people.scope import require_grade_in_scope
from apps.school.labels import section_label
from apps.school.models import Section, Subject
from apps.school.offerings import program_offers_subject
from apps.school.section_progress import recompute_status


class DutyRejected(Exception):
    """The duty cannot be given; the message says why."""


def create_assignment(actor, *, teacher_id, assignment_type, section_id=None, subject_id=None, grade_level='', reason=''):
    """Give a teacher an adviser or subject-teacher duty in the current year, ending the one it replaces.

    Raises DutyRejected for a rule the request breaks. Returns a short summary of the new duty.
    """
    year = current_year()
    if year is None:
        raise DutyRejected('No current school year is set.')
    teacher = get_object_or_404(User, pk=teacher_id, role=User.Role.TEACHER)
    if teacher.account_status in HIDDEN:
        raise DutyRejected('That teacher account is archived.')
    assignment_type = assignment_type or TeacherAssignment.Type.SUBJECT_TEACHER
    allowed = {TeacherAssignment.Type.SUBJECT_TEACHER, TeacherAssignment.Type.ADVISER}
    if assignment_type not in allowed:
        raise DutyRejected('Choose subject teacher or adviser.')
    section = None
    subject = None
    if section_id:
        section = get_object_or_404(Section, pk=section_id, archived_at__isnull=True)
        require_grade_in_scope(actor, section.grade_level)
        if section.school_year.archived_at:
            raise DutyRejected('That section is archived.')
    if subject_id:
        subject = get_object_or_404(Subject, pk=subject_id)
    if assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER and (not section or not subject):
        raise DutyRejected('Subject teachers need a section and a subject.')
    if assignment_type == TeacherAssignment.Type.ADVISER and not section:
        raise DutyRejected('Advisers need a section.')
    if (
        assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER
        and section.program_id
        and not program_offers_subject(section.program, subject)
    ):
        raise DutyRejected(f'{subject.name} is not a {section.program.code} subject.')
    previous = TeacherAssignment.objects.filter(
        section=section,
        school_year=year,
        assignment_type=assignment_type,
        status=TeacherAssignment.Status.ACTIVE,
        **({'subject': subject} if assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER else {}),
    ).select_related('teacher').first()
    if previous:
        previous.status = TeacherAssignment.Status.ENDED
        previous.ended_at = timezone.now()
        previous.save(update_fields=['status', 'ended_at'])
    try:
        row = TeacherAssignment.objects.create(
            teacher=teacher,
            assignment_type=assignment_type,
            school_year=year,
            section=section,
            subject=subject,
            grade_level=section.grade_level if section else grade_level,
            assigned_by=actor,
        )
    except IntegrityError as exc:
        if assignment_type == TeacherAssignment.Type.ADVISER:
            raise DutyRejected('That section already has an adviser.') from exc
        raise DutyRejected('That teacher already has this duty.') from exc
    label = section_label(section) if section else ''
    teacher_name = teacher.get_full_name() or teacher.email
    previous_name = (previous.teacher.get_full_name() or previous.teacher.email) if previous else ''
    if assignment_type == TeacherAssignment.Type.ADVISER:
        audit.record(
            user=actor,
            action='adviser_assigned',
            summary=f'Assigned {teacher_name} as adviser for {label}',
            target_type='TeacherAssignment',
            target_id=row.id,
            details={'previous': previous_name, 'new': teacher_name, 'reason': reason},
        )
        notify(
            [teacher],
            title='Adviser assignment',
            body=f'You are now adviser for {label}.',
            level='info',
            category=ASSIGNMENTS,
            action_path='/teacher/advisory',
        )
    else:
        audit.record(
            user=actor,
            action='subject_teacher_assigned',
            summary=f'Assigned {teacher_name} to {subject.name} · {label}',
            target_type='TeacherAssignment',
            target_id=row.id,
            details={'subject': subject.name, 'previous': previous_name, 'new': teacher_name, 'reason': reason},
        )
        notify(
            [teacher],
            title='Subject assignment',
            body=f'You are assigned to {subject.name} · {label}.',
            level='info',
            category=ASSIGNMENTS,
            action_path='/teacher/classes',
        )
    if section:
        recompute_status(section)
    return {
        'id': row.id,
        'teacher': teacher_name,
        'type': row.assignment_type,
        'section': label,
        'subject': subject.name if subject else '',
    }
