"""Deciding a grade correction, shared by the Head Teacher's screen and approved access requests."""

from django.db import transaction

from apps.audit import services as audit
from apps.audit.catalog import GRADES
from apps.grading.history import HEAD_TEACHER, write_history
from apps.grading.models import CorrectionRequest, Grade
from apps.notifications.services import notify

DECISIONS = (CorrectionRequest.Status.APPROVED, CorrectionRequest.Status.REJECTED)


class CorrectionBlocked(Exception):
    """The correction cannot be decided this way; the message says why."""


def review_correction(row, decision, note, actor):
    """Approve (apply the proposed score) or reject a pending correction, then tell the requester. Returns the row."""
    if decision not in DECISIONS:
        raise CorrectionBlocked('Approve or reject this correction.')
    with transaction.atomic():
        # Locked and read again, so two simultaneous reviews cannot both apply: the second sees it reviewed.
        row = CorrectionRequest.objects.select_for_update().select_related('grade').get(pk=row.pk)
        if row.status != CorrectionRequest.Status.PENDING:
            raise CorrectionBlocked('This correction was already reviewed.')
        if decision == CorrectionRequest.Status.APPROVED and row.grade.status == Grade.Status.RELEASED:
            raise CorrectionBlocked('Hide this student’s report card before applying a correction.')
        row.mark_reviewed(by_user=actor, status=decision, note=note)
        if decision == CorrectionRequest.Status.APPROVED:
            grade = row.grade
            previous = grade.score
            grade.score = row.proposed_score
            grade.updated_by = actor
            grade.save(update_fields=['score', 'updated_by', 'updated_at'])
            write_history(
                grade=grade,
                from_status=grade.status,
                to_status=grade.status,
                previous_score=previous,
                new_score=grade.score,
                user=actor,
                reason='Head teacher approved correction',
                duty=HEAD_TEACHER,
            )
    student = row.grade.student.user.get_full_name()
    audit.record(
        user=actor,
        action='correction_approved' if decision == CorrectionRequest.Status.APPROVED else 'correction_rejected',
        summary=f'{decision.title()} correction for {student} · {row.grade.subject.name}',
        target_type='CorrectionRequest',
        target_id=row.id,
    )
    notify(
        [row.requested_by],
        title=f'Correction {decision}',
        body=f'{actor.get_full_name()} {decision} the correction for {student} · {row.grade.subject.name}.',
        level='warning' if decision == CorrectionRequest.Status.REJECTED else 'success',
        category=GRADES,
        action_path='/teacher/classes',
    )
    return row
