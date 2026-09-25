from apps.people.models import TeacherAssignment


def subject_assignment_for(teacher, assignment_id):
    return (
        TeacherAssignment.objects.filter(
            pk=assignment_id,
            teacher=teacher,
            status=TeacherAssignment.Status.ACTIVE,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            section__isnull=False,
            subject__isnull=False,
        )
        .select_related('section', 'subject', 'school_year')
        .first()
    )


def adviser_assignment_for(teacher, assignment_id):
    return (
        TeacherAssignment.objects.filter(
            pk=assignment_id,
            teacher=teacher,
            status=TeacherAssignment.Status.ACTIVE,
            assignment_type=TeacherAssignment.Type.ADVISER,
            section__isnull=False,
        )
        .select_related('section', 'section__program', 'school_year')
        .first()
    )
