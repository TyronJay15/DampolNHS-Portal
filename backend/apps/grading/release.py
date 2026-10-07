from apps.audit import services as audit
from apps.audit.catalog import GRADES
from apps.grading.advisory import assigned_subject_ids, counted_subject_ids, term_subject_ids
from apps.grading.history import ADVISER
from apps.grading.models import Grade
from apps.grading.transitions import transition_grades
from apps.notifications.services import notify
from apps.people.models import StudentSection


class ReleaseError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def roster_entry(section, student_id):
    return (
        StudentSection.objects.filter(
            section=section,
            student_id=student_id,
            school_year=section.school_year,
            is_active=True,
        )
        .select_related('student', 'student__user')
        .first()
    )


def student_term_grades(section, term, student, statuses=None):
    rows = Grade.objects.filter(
        term=term,
        section=section,
        student=student,
        subject_id__in=assigned_subject_ids(section),
    )
    if statuses is not None:
        rows = rows.filter(status__in=statuses)
    return list(rows)


def student_is_ready(section, term, student):
    """True when every subject scheduled this term (and any already graded) is approved or shown."""
    rows = student_term_grades(section, term, student)
    subject_ids = counted_subject_ids(term_subject_ids(section, term), rows)
    if not subject_ids:
        return False
    grades = {row.subject_id: row for row in rows}
    allowed = {Grade.Status.APPROVED, Grade.Status.RELEASED}
    return all(subject_id in grades and grades[subject_id].status in allowed for subject_id in subject_ids)


def student_can_show(section, term, student):
    return bool(student_term_grades(section, term, student, statuses=[Grade.Status.APPROVED]))


def _notify_student(student, title, body, *, level='success'):
    notify(
        [student.user],
        title=title,
        body=body,
        level=level,
        category=GRADES,
        action_path='/student/grades',
    )


def show_student_card(*, section, term, student, user):
    pending = student_term_grades(section, term, student, statuses=[Grade.Status.APPROVED])
    if not pending:
        raise ReleaseError('No approved grades to show yet.')
    complete = student_is_ready(section, term, student)
    moved = transition_grades(
        grades=pending,
        to_status=Grade.Status.RELEASED,
        user=user,
        reason='Adviser showed report card' if complete else 'Adviser showed partial report card',
        duty=ADVISER,
    )
    if moved:
        shown_rows = student_term_grades(section, term, student, statuses=[Grade.Status.RELEASED])
        assigned = len(counted_subject_ids(term_subject_ids(section, term), shown_rows))
        released = len(shown_rows)
        audit.record(
            user=user,
            action='grades_shown',
            summary=f'Showed {student.user.get_full_name()} report card for {term.label}',
            target_type='StudentProfile',
            target_id=student.id,
            details={'term': term.id, 'section': section.id, 'shown': moved, 'partial': not complete},
        )
        if complete:
            body = f'Your adviser showed your {term.label} grades for {section.name}.'
        else:
            body = (
                f'Your adviser showed a partial {term.label} card for {section.name} '
                f'({released} of {assigned} subjects). More subjects may still be posted.'
            )
        _notify_student(student, f'Report card available · {term.label}', body)
    return moved


def hide_student_card(*, section, term, student, user):
    grades = student_term_grades(section, term, student, statuses=[Grade.Status.RELEASED])
    moved = transition_grades(
        grades=grades,
        to_status=Grade.Status.APPROVED,
        user=user,
        reason='Adviser hid report card',
        duty=ADVISER,
    )
    if not moved:
        return 0
    audit.record(
        user=user,
        action='grades_hidden',
        summary=f'Hid {student.user.get_full_name()} report card for {term.label}',
        target_type='StudentProfile',
        target_id=student.id,
        details={'term': term.id, 'section': section.id, 'hidden': moved},
    )
    _notify_student(
        student,
        f'Report card hidden · {term.label}',
        f'Your adviser hid your {term.label} grades for {section.name}.',
        level='warning',
    )
    return moved


def _roster_students(section):
    return [
        row.student
        for row in StudentSection.objects.filter(
            section=section,
            school_year=section.school_year,
            is_active=True,
        ).select_related('student', 'student__user')
    ]


def show_ready_cards(*, section, term, user):
    shown = 0
    skipped = 0
    for student in _roster_students(section):
        pending = student_term_grades(section, term, student, statuses=[Grade.Status.APPROVED])
        if not pending:
            skipped += 1
            continue
        shown += show_student_card(section=section, term=term, student=student, user=user)
    audit.record(
        user=user,
        action='grades_shown_ready',
        summary=f'Showed {shown} ready report card(s) for {section.name} {term.label}',
        target_type='Section',
        target_id=section.id,
        details={'term': term.id, 'shown': shown, 'skipped': skipped},
    )
    return {'shown': shown, 'skipped': skipped}
