from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTeacher
from apps.grading.progress import assignment_progress, offered_term_ids
from apps.people.models import TeacherAssignment
from apps.school.labels import section_label


class TeacherAssignmentListView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        rows = list(
            TeacherAssignment.objects.filter(
                teacher=request.user,
                status=TeacherAssignment.Status.ACTIVE,
            )
            .select_related('subject', 'section', 'section__program', 'school_year')
            .order_by('assignment_type', 'section__name', 'subject__name')
        )
        offered = offered_term_ids(rows)
        progress = assignment_progress(rows, offered)
        return Response(
            [
                {
                    'id': row.id,
                    'type': row.assignment_type,
                    'school_year': row.school_year.label,
                    'school_year_id': row.school_year_id,
                    'grade_level': row.grade_level or (row.section.grade_level if row.section_id else ''),
                    'program_code': row.section.program.code if row.section_id and row.section.program_id else '',
                    'section_id': row.section_id,
                    'section': section_label(row.section) if row.section_id else '',
                    'section_name': row.section.name if row.section_id else '',
                    'subject_id': row.subject_id,
                    'subject': row.subject.name if row.subject_id else '',
                    'can_encode': row.assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER
                    and bool(row.section_id and row.subject_id),
                    'can_advise': row.assignment_type == TeacherAssignment.Type.ADVISER
                    and bool(row.section_id),
                    'terms': offered.get(row.id, []),
                    'progress': progress.get(row.id),
                }
                for row in rows
            ]
        )
