from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.grading.history import HEAD_TEACHER
from apps.grading.models import Grade
from apps.grading.transitions import transition_grades
from apps.notifications.services import notify
from apps.school.labels import section_label
from apps.school.models import Term


class GradeQueueView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        term = get_object_or_404(Term.objects.select_related('school_year'), pk=request.query_params.get('term'))
        rows = (
            Grade.objects.filter(term=term)
            .values(
                'section_id',
                'section__name',
                'section__grade_level',
                'section__program__code',
                'subject_id',
                'subject__name',
            )
            .annotate(
                draft=Count('id', filter=Q(status=Grade.Status.DRAFT)),
                submitted=Count('id', filter=Q(status=Grade.Status.SUBMITTED)),
                approved=Count('id', filter=Q(status=Grade.Status.APPROVED)),
                released=Count('id', filter=Q(status=Grade.Status.RELEASED)),
            )
            .order_by('section__name', 'subject__name')
        )
        return Response(
            {
                'term': {'id': term.id, 'label': term.label, 'school_year': term.school_year.label},
                'groups': [
                    {
                        'section_id': row['section_id'],
                        'section': section_label(
                            grade_level=row['section__grade_level'],
                            program_code=row['section__program__code'] or '',
                            name=row['section__name'] or '',
                        )
                        or 'Unassigned',
                        'subject_id': row['subject_id'],
                        'subject': row['subject__name'],
                        'draft': row['draft'],
                        'submitted': row['submitted'],
                        'approved': row['approved'],
                        'released': row['released'],
                    }
                    for row in rows
                ],
            }
        )


class ApproveGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        pending = list(
            Grade.objects.filter(
                term=term,
                section_id=request.data.get('section'),
                subject_id=request.data.get('subject'),
                status=Grade.Status.SUBMITTED,
            )
        )
        teachers = {row.teacher for row in pending if row.teacher_id}
        moved = transition_grades(
            grades=pending,
            to_status=Grade.Status.APPROVED,
            user=request.user,
            reason='Head teacher approved grades',
            duty=HEAD_TEACHER,
        )
        audit.record(
            user=request.user,
            action='grades_approved',
            summary=f'Approved {moved} submitted grades for {term.label}',
            target_type='Term',
            target_id=term.id,
        )
        if moved:
            notify(
                teachers,
                title=f'{term.label} grades approved',
                body=f'{request.user.get_full_name()} approved the submitted class for {term.label}.',
            )
        return Response({'approved': moved})


class ReturnGradesView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        term = get_object_or_404(Term, pk=request.data.get('term'))
        section_id = request.data.get('section')
        subject_id = request.data.get('subject')
        shown = Grade.objects.filter(
            term=term,
            section_id=section_id,
            subject_id=subject_id,
            status=Grade.Status.RELEASED,
        ).count()
        grades = list(
            Grade.objects.filter(
                term=term,
                section_id=section_id,
                subject_id=subject_id,
                status__in=[Grade.Status.SUBMITTED, Grade.Status.APPROVED],
            )
        )
        if not grades:
            if shown:
                return Response(
                    {
                        'detail': (
                            f'{shown} shown card(s) were left untouched. '
                            'Hide those students first if you need their grades returned.'
                        )
                    },
                    status=400,
                )
            return Response({'detail': 'There are no submitted or approved grades to return.'}, status=400)
        moved = transition_grades(
            grades=grades,
            to_status=Grade.Status.DRAFT,
            user=request.user,
            reason='Head teacher returned grades',
            duty=HEAD_TEACHER,
        )
        audit.record(
            user=request.user,
            action='grades_returned',
            summary=f'Returned {moved} hidden grades to draft for {term.label}',
            target_type='Term',
            target_id=term.id,
            details={'still_shown': shown},
        )
        if moved:
            notify(
                {row.teacher for row in grades if row.teacher_id},
                title=f'{term.label} grades returned',
                body=f'{request.user.get_full_name()} returned {term.label} grades to draft. Fix and submit again.',
            )
        return Response({'returned': moved, 'still_shown': shown})
