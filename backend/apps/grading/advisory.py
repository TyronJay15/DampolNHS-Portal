from apps.accounts.lifecycle import HIDDEN
from apps.grading.models import Grade
from apps.grading.recommend import recommend_payload
from apps.people.models import StudentSection, TeacherAssignment


def section_roster(section):
    return list(
        StudentSection.objects.filter(
            section=section,
            school_year=section.school_year,
            is_active=True,
        ).exclude(student__user__account_status__in=HIDDEN)
        .select_related('student', 'student__user')
        .order_by('student__user__last_name', 'student__user__first_name')
    )


def section_subject_assignments(section):
    return list(
        TeacherAssignment.objects.filter(
            section=section,
            school_year=section.school_year,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            status=TeacherAssignment.Status.ACTIVE,
            subject__isnull=False,
        )
        .select_related('subject', 'teacher')
        .order_by('subject__name')
    )


def assigned_subject_ids(section):
    return [row.subject_id for row in section_subject_assignments(section)]


def _counts(roster_ids, grades_by_student):
    counts = {'missing': 0, 'draft': 0, 'submitted': 0, 'approved': 0, 'released': 0}
    for student_id in roster_ids:
        grade = grades_by_student.get(student_id)
        if grade is None:
            counts['missing'] += 1
        elif grade.status in counts:
            counts[grade.status] += 1
    return counts


def _student_state(subject_ids, grades):
    by_subject = {row.subject_id: row for row in grades}
    missing = draft = submitted = approved = released = 0
    for subject_id in subject_ids:
        grade = by_subject.get(subject_id)
        if grade is None:
            missing += 1
        elif grade.status == Grade.Status.DRAFT:
            draft += 1
        elif grade.status == Grade.Status.SUBMITTED:
            submitted += 1
        elif grade.status == Grade.Status.APPROVED:
            approved += 1
        elif grade.status == Grade.Status.RELEASED:
            released += 1
    ready = bool(subject_ids) and missing == 0 and draft == 0 and submitted == 0
    shown = bool(subject_ids) and released == len(subject_ids)
    return {
        'ready': ready,
        'shown': shown,
        'has_released': released > 0,
    }


def advisory_snapshot(section, term):
    roster = section_roster(section)
    assignments = section_subject_assignments(section)
    subject_ids = [row.subject_id for row in assignments]
    roster_ids = [row.student_id for row in roster]
    year_grades = list(
        Grade.objects.filter(student_id__in=roster_ids, school_year=section.school_year)
        .filter(status__in=[Grade.Status.APPROVED, Grade.Status.RELEASED])
        .select_related('subject')
    )
    grades_by_student = {}
    for grade in year_grades:
        grades_by_student.setdefault(grade.student_id, []).append(grade)

    term_grades = list(Grade.objects.filter(section=section, term=term, subject_id__in=subject_ids))
    term_by_subject = {}
    term_by_student = {}
    for grade in term_grades:
        term_by_subject.setdefault(grade.subject_id, {})[grade.student_id] = grade
        term_by_student.setdefault(grade.student_id, []).append(grade)

    subjects = []
    for assignment in assignments:
        counts = _counts(roster_ids, term_by_subject.get(assignment.subject_id, {}))
        subjects.append(
            {
                'subject_id': assignment.subject_id,
                'subject': assignment.subject.name,
                'teacher': assignment.teacher.get_full_name() or assignment.teacher.email,
                **counts,
                'ready': bool(roster_ids) and counts['missing'] == 0 and counts['draft'] == 0 and counts['submitted'] == 0,
            }
        )

    students = []
    for row in roster:
        state = _student_state(subject_ids, term_by_student.get(row.student_id, []))
        students.append(
            {
                'student_id': row.student_id,
                'name': row.student.user.get_full_name(),
                'lrn': row.student.lrn,
                'contact_number': row.student.contact_number,
                'guardian_name': row.student.guardian_name,
                'guardian_contact': row.student.guardian_contact,
                'ready': state['ready'],
                'shown': state['shown'],
                'can_show': state['ready'] and not state['shown'],
                'can_hide': state['has_released'],
                'recommendation': recommend_payload(grades_by_student.get(row.student_id, [])),
            }
        )

    return {
        'section': {
            'id': section.id,
            'name': section.name,
            'grade_level': section.grade_level,
            'program': section.program.code if section.program_id else '',
        },
        'term': {'id': term.id, 'label': term.label, 'number': term.number},
        'roster_count': len(roster),
        'subjects': subjects,
        'students': students,
    }
