"""Section setup progress, readiness checks, and status helpers."""

from apps.people.models import TeacherAssignment
from apps.school.models import Section
from apps.school.offerings import subject_payloads_for_program


def _active_adviser(section):
    return (
        TeacherAssignment.objects.filter(
            section=section,
            school_year=section.school_year,
            assignment_type=TeacherAssignment.Type.ADVISER,
            status=TeacherAssignment.Status.ACTIVE,
        )
        .select_related('teacher')
        .first()
    )


def _subject_assignments(section):
    return TeacherAssignment.objects.filter(
        section=section,
        school_year=section.school_year,
        assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
        status=TeacherAssignment.Status.ACTIVE,
    ).select_related('teacher', 'subject')


def required_subjects(section):
    if not section.program_id:
        return []
    return subject_payloads_for_program(section.program)


def section_progress(section):
    student_count = section.student_assignments.filter(is_active=True).count()
    capacity = section.capacity or 0
    adviser_row = _active_adviser(section)
    required = required_subjects(section)
    assigned_by_subject = {
        row.subject_id: row for row in _subject_assignments(section) if row.subject_id
    }
    assigned_count = sum(1 for subj in required if subj['id'] in assigned_by_subject)
    required_count = len(required)

    subject_rows = []
    for subj in required:
        duty = assigned_by_subject.get(subj['id'])
        subject_rows.append(
            {
                'subject_id': subj['id'],
                'subject': subj['name'],
                'teacher_id': duty.teacher_id if duty else None,
                'teacher': (duty.teacher.get_full_name() or duty.teacher.email) if duty else '',
                'assigned': bool(duty),
            }
        )

    checklist = [
        {
            'key': 'section_info',
            'label': 'Section information',
            'detail': 'School year, grade, program, and section name configured.',
            'done': bool(section.name and section.grade_level and section.program_id and section.school_year_id),
        },
        {
            'key': 'students',
            'label': 'Student assignment',
            'detail': f'{student_count} student{"s" if student_count != 1 else ""} assigned.'
            + (f' Capacity {student_count}/{capacity}.' if capacity else ''),
            'done': student_count > 0,
        },
        {
            'key': 'adviser',
            'label': 'Adviser',
            'detail': (
                (adviser_row.teacher.get_full_name() or adviser_row.teacher.email)
                if adviser_row
                else 'No adviser assigned yet.'
            ),
            'done': bool(adviser_row),
        },
        {
            'key': 'subject_teachers',
            'label': 'Subject teachers',
            'detail': f'{assigned_count} of {required_count} required subject assignments completed.',
            'done': required_count == 0 or assigned_count >= required_count,
        },
    ]

    done_count = sum(1 for item in checklist if item['done'])
    progress_percent = round((done_count / len(checklist)) * 100) if checklist else 0
    ready = all(item['done'] for item in checklist) and required_count > 0

    missing = [item['label'] for item in checklist if not item['done']]
    if required_count == 0 and section.program_id:
        missing.append('Program has no subjects in the catalog')

    return {
        'student_count': student_count,
        'capacity': capacity,
        'at_capacity': bool(capacity and student_count >= capacity),
        'adviser_id': adviser_row.teacher_id if adviser_row else None,
        'adviser': (
            (adviser_row.teacher.get_full_name() or adviser_row.teacher.email) if adviser_row else ''
        ),
        'required_subjects': required_count,
        'assigned_subjects': assigned_count,
        'subject_rows': subject_rows,
        'checklist': checklist,
        'progress_percent': progress_percent,
        'ready': ready and required_count > 0,
        'missing': missing,
    }


def recompute_status(section):
    """Update DRAFT / IN PROGRESS / READY based on setup state. Never downgrade ACTIVE."""
    if section.archived_at:
        if section.status != Section.Status.ARCHIVED:
            section.status = Section.Status.ARCHIVED
            section.save(update_fields=['status'])
        return section.status

    if section.status == Section.Status.ACTIVE:
        return section.status

    previous = section.status
    data = section_progress(section)
    if data['ready']:
        next_status = Section.Status.READY
    elif data['student_count'] or data['adviser'] or data['assigned_subjects']:
        next_status = Section.Status.IN_PROGRESS
    else:
        next_status = Section.Status.DRAFT

    if section.status != next_status:
        section.status = next_status
        section.save(update_fields=['status'])
        if next_status == Section.Status.READY and previous != Section.Status.READY:
            from apps.audit.catalog import SCHOOL
            from apps.notifications.services import head_teachers, notify
            from apps.school.labels import section_label

            notify(
                head_teachers(),
                title='Section ready to activate',
                body=f'{section_label(section)} has completed setup and can be activated.',
                level='success',
                category=SCHOOL,
                action_path=f'/head/sections/{section.id}/setup?step=review',
            )
    return section.status


def activation_checks(section):
    data = section_progress(section)
    checks = [
        {'key': 'school_year', 'label': 'School year selected', 'ok': bool(section.school_year_id)},
        {'key': 'grade_level', 'label': 'Grade level selected', 'ok': bool(section.grade_level)},
        {'key': 'program', 'label': 'Program selected', 'ok': bool(section.program_id)},
        {'key': 'name', 'label': 'Section name configured', 'ok': bool(section.name)},
        {
            'key': 'students',
            'label': 'Students assigned',
            'ok': data['student_count'] > 0,
        },
        {'key': 'adviser', 'label': 'Adviser assigned', 'ok': bool(data['adviser'])},
        {
            'key': 'subjects',
            'label': 'Required subject teachers assigned',
            'ok': data['required_subjects'] > 0 and data['assigned_subjects'] >= data['required_subjects'],
        },
        {
            'key': 'capacity',
            'label': 'Section capacity not exceeded',
            'ok': not section.capacity or data['student_count'] <= section.capacity,
        },
    ]
    blocked = [row['label'] for row in checks if not row['ok']]
    return {'checks': checks, 'can_activate': not blocked, 'blocked': blocked}
