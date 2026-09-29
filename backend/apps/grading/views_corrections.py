from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.grading.history import HEAD_TEACHER, write_history
from apps.grading.models import CorrectionRequest, Grade
from apps.grading.scores import parse_score
from apps.audit.catalog import GRADES
from apps.notifications.services import head_teachers, notify
from apps.people.assignment_access import subject_assignment_for
from apps.school.labels import section_label


def _payload(row):
    grade = row.grade
    return {
        'id': row.id,
        'grade_id': row.grade_id,
        'student': row.grade.student.user.get_full_name(),
        'lrn': row.grade.student.lrn,
        'subject': row.grade.subject.name,
        'section': section_label(row.grade.section) if row.grade.section_id else '',
        'term': row.grade.term.label,
        'current_score': str(row.current_score),
        'proposed_score': str(row.proposed_score),
        'reason': row.reason,
        'status': row.status,
        'grade_status': grade.status,
        'approve_blocked': grade.status == Grade.Status.RELEASED,
        'approve_block_reason': (
            'Hide this student’s report card before approving this correction.'
            if grade.status == Grade.Status.RELEASED
            else ''
        ),
        'requested_by': row.requested_by.get_full_name() if row.requested_by_id else '',
        'reviewed_by': row.reviewed_by.get_full_name() if row.reviewed_by_id else '',
        'review_note': row.review_note,
        'reviewed_at': row.reviewed_at,
        'created_at': row.created_at,
    }


class CorrectionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('head_teacher', 'teacher'):
            return Response({'detail': 'You cannot view correction requests.'}, status=403)
        rows = CorrectionRequest.objects.select_related(
            'grade__student__user',
            'grade__subject',
            'grade__section',
            'grade__section__program',
            'grade__term',
            'requested_by',
            'reviewed_by',
        )
        if request.user.role == 'teacher':
            rows = rows.filter(requested_by=request.user)
        status = request.query_params.get('status')
        if status == 'record':
            rows = rows.filter(status__in=[CorrectionRequest.Status.APPROVED, CorrectionRequest.Status.REJECTED])
        elif status:
            rows = rows.filter(status=status)
        elif request.user.role == 'head_teacher':
            rows = rows.filter(status=CorrectionRequest.Status.PENDING)
        return Response([_payload(row) for row in rows[:100]])

    def post(self, request):
        if request.user.role != 'teacher':
            return Response({'detail': 'Only the subject teacher can request a correction.'}, status=403)
        assignment = subject_assignment_for(request.user, request.data.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You cannot correct grades for that class.'}, status=403)
        grade = get_object_or_404(
            Grade.objects.select_related('student__user', 'subject', 'section', 'term'),
            pk=request.data.get('grade'),
            subject=assignment.subject,
            section=assignment.section,
        )
        if grade.status == Grade.Status.DRAFT:
            return Response({'detail': 'Draft grades can be edited directly.'}, status=400)
        score = parse_score(request.data.get('proposed_score'))
        if score is None:
            return Response({'detail': 'Enter a grade from 0 to 100.'}, status=400)
        if score == grade.score:
            return Response({'detail': 'The proposed grade is the same as the current grade.'}, status=400)
        reason = str(request.data.get('reason') or '').strip()
        if not reason:
            return Response({'detail': 'Explain why this grade should change.'}, status=400)
        if CorrectionRequest.objects.filter(grade=grade, status=CorrectionRequest.Status.PENDING).exists():
            return Response({'detail': 'A correction is already pending for this grade.'}, status=400)
        row = CorrectionRequest.objects.create(
            grade=grade,
            requested_by=request.user,
            current_score=grade.score,
            proposed_score=score,
            reason=reason,
        )
        audit.record(
            user=request.user,
            action='correction_requested',
            summary=f'Requested correction for {grade.student.user.get_full_name()} · {grade.subject.name}',
            target_type='CorrectionRequest',
            target_id=row.id,
            details={'from': str(grade.score), 'to': str(score)},
        )
        notify(
            head_teachers(),
            title='Correction requested',
            body=f'{request.user.get_full_name()} asked to change {grade.student.user.get_full_name()} · {grade.subject.name}.',
            category=GRADES,
            action_path='/head/corrections',
        )
        return Response(_payload(row), status=201)


class CorrectionReviewView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        row = get_object_or_404(
            CorrectionRequest.objects.select_related(
                'grade__student__user',
                'grade__subject',
                'grade__section',
                'grade__term',
                'requested_by',
            ),
            pk=pk,
        )
        if row.status != CorrectionRequest.Status.PENDING:
            return Response({'detail': 'This correction was already reviewed.'}, status=400)
        decision = request.data.get('status')
        if decision not in (CorrectionRequest.Status.APPROVED, CorrectionRequest.Status.REJECTED):
            return Response({'detail': 'Approve or reject this correction.'}, status=400)
        if decision == CorrectionRequest.Status.APPROVED and row.grade.status == Grade.Status.RELEASED:
            return Response(
                {'detail': 'Hide this student’s report card before applying a correction.'},
                status=400,
            )
        note = str(request.data.get('note') or '').strip()
        with transaction.atomic():
            row.mark_reviewed(by_user=request.user, status=decision, note=note)
            if decision == CorrectionRequest.Status.APPROVED:
                grade = row.grade
                previous = grade.score
                grade.score = row.proposed_score
                grade.updated_by = request.user
                grade.save(update_fields=['score', 'updated_by', 'updated_at'])
                write_history(
                    grade=grade,
                    from_status=grade.status,
                    to_status=grade.status,
                    previous_score=previous,
                    new_score=grade.score,
                    user=request.user,
                    reason='Head teacher approved correction',
                    duty=HEAD_TEACHER,
                )
        audit.record(
            user=request.user,
            action='correction_approved' if decision == CorrectionRequest.Status.APPROVED else 'correction_rejected',
            summary=f'{decision.title()} correction for {row.grade.student.user.get_full_name()} · {row.grade.subject.name}',
            target_type='CorrectionRequest',
            target_id=row.id,
        )
        notify(
            [row.requested_by],
            title=f'Correction {decision}',
            body=f'{request.user.get_full_name()} {decision} the correction for {row.grade.student.user.get_full_name()} · {row.grade.subject.name}.',
            level='warning' if decision == CorrectionRequest.Status.REJECTED else 'success',
            category=GRADES,
            action_path='/teacher/classes',
        )
        return Response(_payload(row))
