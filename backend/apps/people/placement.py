"""Placing students in sections, shared by the Head Teacher's screens and approved access requests."""

from django.utils import timezone

from apps.accounts.lifecycle import HIDDEN
from apps.audit import services as audit
from apps.audit.catalog import PLACEMENT
from apps.notifications.services import advisers_for_section, head_teachers, notify
from apps.people.models import Registration, StudentSection
from apps.school.labels import section_label
from apps.school.models import SchoolYear
from apps.school.section_progress import recompute_status

TRANSFER_TITLE = 'Roster change · transfer'
PLACEMENT_TITLE = 'Roster change · placement'


def current_year():
    return SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()


def _current_placement(student, year):
    return (
        StudentSection.objects.filter(student=student, school_year=year, is_active=True)
        .select_related('section', 'section__program', 'section__school_year')
        .first()
    )


def _notify_placement(student, old_section, section, transfer):
    name = student.user.get_full_name() or student.lrn
    label = section_label(section)
    if transfer and old_section:
        notify(
            advisers_for_section(old_section) + advisers_for_section(section),
            title=TRANSFER_TITLE,
            body=f'{name} moved from {section_label(old_section)} to {label}.',
            category=PLACEMENT,
            action_path='/teacher/advisory',
        )
        return
    notify(
        advisers_for_section(section),
        title=PLACEMENT_TITLE,
        body=f'{name} was placed in {label}.',
        category=PLACEMENT,
        action_path='/teacher/advisory',
    )


def _section_count(section):
    return section.student_assignments.filter(is_active=True).count()


def _capacity_error(section, incoming=1, override=False):
    if not section.capacity:
        return None
    count = _section_count(section)
    if count + incoming > section.capacity and not override:
        return (
            f'This section is at capacity ({count}/{section.capacity}). '
            'Confirm to exceed the limit.'
        )
    return None


def place_student(student, section, year, user, transfer=False, override_capacity=False, reason=''):
    if student.user.account_status in HIDDEN:
        return 'That student account is archived.'
    registration = approved_registration(student.user)
    if (
        not transfer
        and registration
        and section.program_id
        and registration.program_id != section.program_id
    ):
        return 'Place the student in a section of their enrolled program.'
    grade = student_grade(student, registration)
    if grade and section.grade_level and grade != section.grade_level:
        return 'Place the student in a section of their grade level.'
    if section.archived_at or section.school_year.archived_at:
        return 'That section is archived.'
    current = _current_placement(student, year)
    old_section = current.section if current else None
    if old_section and old_section.id == section.id:
        return None
    cap_error = _capacity_error(section, override=override_capacity)
    if cap_error:
        return cap_error
    StudentSection.objects.filter(student=student, school_year=year, is_active=True).update(
        is_active=False,
        ended_at=timezone.now(),
    )
    StudentSection.objects.create(
        student=student,
        section=section,
        school_year=year,
        assigned_by=user,
    )
    old_program = _follow_section_program(registration, section, year)
    name = student.user.get_full_name() or student.lrn
    label = section_label(section)
    if transfer or old_section:
        audit.record(
            user=user,
            action='student_transferred',
            summary=f'Transferred {name} to {label}',
            target_type='StudentSection',
            target_id=student.id,
            details={
                'student': name,
                'from': section_label(old_section) if old_section else '',
                'to': label,
                'program_from': old_program.code if old_program else '',
                'program_to': section.program.code if old_program else '',
                'reason': reason,
            },
        )
        program_note = f' Program changed from {old_program.code} to {section.program.code}.' if old_program else ''
        notify(
            head_teachers(),
            title=TRANSFER_TITLE,
            body=f'{name} was transferred to {label}.{program_note}',
            level='info',
            category=PLACEMENT,
            action_path=f'/head/sections/{section.id}/setup?step=students',
        )
    else:
        audit.record(
            user=user,
            action='student_placed',
            summary=f'Placed {name} in {label}',
            target_type='StudentSection',
            target_id=student.id,
            details={'student': name, 'section': label, 'reason': reason},
        )
    _notify_placement(student, old_section, section, transfer or bool(old_section))
    recompute_status(section)
    if old_section and old_section.id != section.id:
        recompute_status(old_section)
    return None


def _follow_section_program(registration, section, year):
    """A transfer into another program's section moves this year's registration with it.

    Registrations from earlier years stay as they were, so enrollment history is kept.
    Returns the previous program when it changed, else None.
    """
    if (
        registration is None
        or not section.program_id
        or registration.program_id == section.program_id
        or registration.school_year_id != year.id
    ):
        return None
    old_program = registration.program
    registration.program = section.program
    registration.save(update_fields=['program'])
    return old_program


def approved_registration(user):
    return (
        Registration.objects.filter(user=user, status=Registration.Status.APPROVED)
        .select_related('program')
        .first()
    )


def student_grade(profile, registration):
    return profile.grade_level or (registration.grade_level_enrollment if registration else '')


def student_program(profile, registration, placement=None):
    if placement and placement.section and placement.section.program_id:
        return placement.section.program
    if registration:
        return registration.program
    return None
