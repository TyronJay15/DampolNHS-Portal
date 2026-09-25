SUBJECT_TEACHER = 'subject_teacher'
ADVISER = 'adviser'
HEAD_TEACHER = 'head_teacher'


def write_history(*, grade, from_status, to_status, previous_score, new_score, user, reason, duty):
    from apps.grading.models import GradeHistory

    return GradeHistory.objects.create(
        grade=grade,
        from_status=from_status or '',
        to_status=to_status,
        previous_score=previous_score,
        new_score=new_score,
        changed_by=user,
        duty=duty,
        reason=reason,
    )
