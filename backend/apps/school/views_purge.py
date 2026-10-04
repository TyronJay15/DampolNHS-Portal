from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section
from apps.school.purge import purge_school_year, purge_section, section_delete_summary, year_delete_summary


class SectionPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        section = get_object_or_404(Section.objects.select_related('program', 'school_year'), pk=pk)
        hard = bool(request.data.get('hard'))
        confirm = str(request.data.get('confirm') or '').strip()
        reason = str(request.data.get('reason') or '').strip()
        label = section_label(section)
        summary = section_delete_summary(section)
        if summary['grades'] and hard:
            if confirm != section.name:
                return Response({'detail': 'Type the section short name exactly to hard delete.'}, status=400)
            if not reason:
                return Response({'detail': 'Provide a reason for hard delete.'}, status=400)
        error, _ = purge_section(section, hard=hard)
        if error:
            return Response({'detail': error, 'summary': summary, 'grades_protected': summary['grades'] > 0}, status=400)
        audit.record(
            user=request.user,
            action='section_hard_deleted' if hard and summary['grades'] else 'section_deleted',
            summary=f'{"Hard deleted" if hard else "Deleted"} {label}',
            target_type='Section',
            target_id=pk,
            details={'reason': reason, **summary},
        )
        return Response({'id': pk, 'deleted': True})


class SchoolYearPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        hard = bool(request.data.get('hard'))
        confirm = str(request.data.get('confirm') or '').strip()
        reason = str(request.data.get('reason') or '').strip()
        summary = year_delete_summary(year)
        if summary['grades'] and hard:
            if confirm != year.label:
                return Response({'detail': 'Type the school year label exactly to hard delete.'}, status=400)
            if not reason:
                return Response({'detail': 'Provide a reason for hard delete.'}, status=400)
        error, _ = purge_school_year(year, hard=hard)
        if error:
            return Response({'detail': error, 'summary': summary, 'grades_protected': summary['grades'] > 0}, status=400)
        audit.record(
            user=request.user,
            action='school_year_hard_deleted' if hard and summary['grades'] else 'school_year_deleted',
            summary=f'{"Hard deleted" if hard else "Deleted"} {year.label}',
            target_type='SchoolYear',
            target_id=pk,
            details={'reason': reason, **summary},
        )
        return Response({'id': pk, 'deleted': True})
