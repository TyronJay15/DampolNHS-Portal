from django.db import transaction
from django.utils import timezone

from apps.grading.history import write_history
from apps.grading.models import Grade


def transition_grades(*, grades, to_status, user, reason, duty):
    """Move grades to a new status and write their history. Returns how many moved.

    The rows are locked and read again first. A grade only moves if it is still in the status the caller saw, so
    two simultaneous requests (a double click, two tabs) move each grade once: the second request moves nothing.
    """
    now = timezone.now()
    moved = 0
    with transaction.atomic():
        current = dict(
            Grade.objects.select_for_update().filter(pk__in=[grade.pk for grade in grades]).values_list('pk', 'status')
        )
        for grade in grades:
            previous_status = grade.status
            if previous_status == to_status or current.get(grade.pk) != previous_status:
                continue
            moved += _move(grade, previous_status, to_status, user, reason, duty, now)
    return moved


def _move(grade, previous_status, to_status, user, reason, duty, now):
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
    return 1
