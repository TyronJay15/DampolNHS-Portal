from django.utils import timezone

from apps.audit import services as audit
from apps.grading.advisory import assigned_subject_ids
from apps.grading.history import ADVISER
from apps.grading.models import Grade, PtpaAttendance
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


def ptpa_attended(student, term):
    return PtpaAttendance.objects.filter(student=student, term=term, attended=True).exists()


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
    subject_ids = assigned_subject_ids(section)
    if not subject_ids:
        return False
    grades = {row.subject_id: row for row in student_term_grades(section, term, student)}
    if len(grades) != len(subject_ids):
        return False
    allowed = {Grade.Status.APPROVED, Grade.Status.RELEASED}
    return all(grades[subject_id].status in allowed for subject_id in subject_ids)


def _notify_student(student, title, body):
    notify([student.user], title=title, body=body)


def show_student_card(*, section, term, student, user):
    if not student_is_ready(section, term, student):
        raise ReleaseError('Every assigned subject for this student must be approved first.')
    grades = student_term_grades(section, term, student, statuses=[Grade.Status.APPROVED])
    moved = transition_grades(
        grades=grades,
        to_status=Grade.Status.RELEASED,
        user=user,
        reason='Adviser showed report card',
        duty=ADVISER,
    )
    audit.record(
        user=user,
        action='grades_shown',
        summary=f'Showed {student.user.get_full_name()} report card for {term.label}',
        target_type='StudentProfile',
        target_id=student.id,
        details={'term': term.id, 'section': section.id, 'shown': moved},
    )
    if moved:
        _notify_student(
            student,
            f'{term.label} report card is available',
            f'Your adviser showed your {term.label} grades for {section.name}.',
        )
    return moved


def hide_student_card(*, section, term, student, user, reason='Adviser hid report card'):
    grades = student_term_grades(section, term, student, statuses=[Grade.Status.RELEASED])
    moved = transition_grades(
        grades=grades,
        to_status=Grade.Status.APPROVED,
        user=user,
        reason=reason,
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
        f'{term.label} report card was hidden',
        f'Your adviser hid your {term.label} grades for {section.name}.',
    )
    return moved


def set_ptpa(*, section, term, student, attended, user):
    PtpaAttendance.objects.update_or_create(
        student=student,
        term=term,
        defaults={
            'section': section,
            'attended': attended,
            'marked_by': user,
            'marked_at': timezone.now(),
        },
    )
    hidden = 0
    if not attended:
        hidden = hide_student_card(
            section=section,
            term=term,
            student=student,
            user=user,
            reason='Parent missed PTPA',
        )
    audit.record(
        user=user,
        action='ptpa_marked',
        summary=f'Marked PTPA {"attended" if attended else "absent"} for {student.user.get_full_name()}',
        target_type='StudentProfile',
        target_id=student.id,
        details={'term': term.id, 'section': section.id, 'attended': attended, 'hidden': hidden},
    )
    return hidden


def _students_on_roster(section, student_ids):
    if student_ids is None:
        return [
            row.student
            for row in StudentSection.objects.filter(
                section=section,
                school_year=section.school_year,
                is_active=True,
            ).select_related('student', 'student__user')
        ]
    if not isinstance(student_ids, (list, tuple)) or not student_ids:
        raise ReleaseError('Choose at least one student.')
    students = []
    for student_id in student_ids:
        placement = roster_entry(section, student_id)
        if placement is None:
            raise ReleaseError('That student is not in this advisory section.', status=404)
        students.append(placement.student)
    return students


def set_ptpa_bulk(*, section, term, student_ids, attended, user):
    students = _students_on_roster(section, student_ids)
    hidden = 0
    for student in students:
        hidden += set_ptpa(section=section, term=term, student=student, attended=attended, user=user)
    return {'marked': len(students), 'hidden': hidden, 'attended': attended}


def show_ready_cards(*, section, term, user):
    shown = 0
    skipped = 0
    for student in _students_on_roster(section, None):
        if not student_is_ready(section, term, student):
            skipped += 1
            continue
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
