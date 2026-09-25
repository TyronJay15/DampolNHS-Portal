from django.utils import timezone

from apps.grading.history import write_history
from apps.grading.models import Grade


def transition_grades(*, grades, to_status, user, reason, duty):
    now = timezone.now()
    moved = 0
    for grade in grades:
        previous_status = grade.status
        if previous_status == to_status:
            continue
        grade.status = to_status
        grade.updated_by = user
        fields = ['status', 'updated_by', 'updated_at']
        if to_status == Grade.Status.APPROVED:
            grade.approved_at = now
            grade.released_at = None
            fields.extend(['approved_at', 'released_at'])
        elif to_status == Grade.Status.RELEASED:
            grade.released_at = now
            fields.append('released_at')
        elif to_status == Grade.Status.DRAFT:
            grade.approved_at = None
            grade.released_at = None
            fields.extend(['approved_at', 'released_at'])
        grade.save(update_fields=fields)
        write_history(
            grade=grade,
            from_status=previous_status,
            to_status=to_status,
            previous_score=grade.score,
            new_score=grade.score,
            user=user,
            reason=reason,
            duty=duty,
        )
        moved += 1
    return moved
