from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.grading.models import Grade
from apps.people.models import TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section
from apps.school.serializers import SchoolYearSerializer, SectionSerializer


def _year_busy(year):
    return year.sections.exists()


def _section_busy(section):
    if section.student_assignments.exists() or section.teacher_assignments.exists():
        return True
    return Grade.objects.filter(section=section).exists()


class SchoolYearArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk, archived_at__isnull=True)
        if year.is_current:
            return Response({'detail': 'Make another year current before archiving this one.'}, status=400)
        now = timezone.now()
        year.archived_at = now
        year.is_current = False
        year.save(update_fields=['archived_at', 'is_current'])
        year.sections.filter(archived_at__isnull=True).update(archived_at=now, is_active=False)
        TeacherAssignment.objects.filter(school_year=year, status=TeacherAssignment.Status.ACTIVE).update(
            status=TeacherAssignment.Status.ENDED,
            ended_at=now,
        )
        audit.record(
            user=request.user,
            action='school_year_archived',
            summary=f'Archived school year {year.label}',
            target_type='SchoolYear',
            target_id=year.id,
        )
        return Response(SchoolYearSerializer(year).data)


class SchoolYearRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        if year.archived_at is None:
            return Response({'detail': 'That year is already live.'}, status=400)
        year.archived_at = None
        year.save(update_fields=['archived_at'])
        year.sections.exclude(archived_at=None).update(archived_at=None, is_active=True)
        audit.record(
            user=request.user,
            action='school_year_restored',
            summary=f'Restored school year {year.label}',
            target_type='SchoolYear',
            target_id=year.id,
        )
        return Response(SchoolYearSerializer(year).data)


class SchoolYearDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def delete(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        if year.is_current:
            return Response({'detail': 'The current school year cannot be deleted.'}, status=400)
        if year.archived_at or _year_busy(year):
            return Response({'detail': 'Archive a year that has sections or grades. Delete only an empty year.'}, status=400)
        label = year.label
        year.delete()
        audit.record(
            user=request.user,
            action='school_year_deleted',
            summary=f'Deleted empty school year {label}',
            target_type='SchoolYear',
            target_id=pk,
        )
        return Response({'id': pk, 'deleted': True})


class SectionArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        section = get_object_or_404(Section.objects.select_related('program', 'school_year'), pk=pk)
        if section.archived_at:
            return Response({'detail': 'That section is already archived.'}, status=400)
        now = timezone.now()
        section.archived_at = now
        section.is_active = False
        section.save(update_fields=['archived_at', 'is_active'])
        TeacherAssignment.objects.filter(section=section, status=TeacherAssignment.Status.ACTIVE).update(
            status=TeacherAssignment.Status.ENDED,
            ended_at=now,
        )
        audit.record(
            user=request.user,
            action='section_archived',
            summary=f'Archived {section_label(section)}',
            target_type='Section',
            target_id=section.id,
        )
        return Response(SectionSerializer(section).data)


class SectionRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        section = get_object_or_404(Section.objects.select_related('program', 'school_year'), pk=pk)
        if section.archived_at is None:
            return Response({'detail': 'That section is already live.'}, status=400)
        if section.school_year.archived_at:
            return Response({'detail': 'Restore the school year first.'}, status=400)
        section.archived_at = None
        section.is_active = True
        section.save(update_fields=['archived_at', 'is_active'])
        audit.record(
            user=request.user,
            action='section_restored',
            summary=f'Restored {section_label(section)}',
            target_type='Section',
            target_id=section.id,
        )
        return Response(SectionSerializer(section).data)


class SectionRosterView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request, pk):
        section = get_object_or_404(Section.objects.select_related('program', 'school_year'), pk=pk)
        rows = section.student_assignments.filter(is_active=True).select_related('student', 'student__user')
        return Response(
            {
                'section': SectionSerializer(section).data,
                'students': [
                    {
                        'student_id': row.student_id,
                        'name': row.student.user.get_full_name(),
                        'lrn': row.student.lrn,
                        'contact_number': row.student.contact_number,
                    }
                    for row in rows.order_by('student__user__last_name', 'student__user__first_name')
                ],
            }
        )


class ArchiveDeskView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        kind = (request.query_params.get('kind') or 'sections').strip()
        year_id = request.query_params.get('school_year')
        if kind == 'years':
            rows = SchoolYear.objects.filter(archived_at__isnull=False)
            return Response(SchoolYearSerializer(rows, many=True).data)
        if kind == 'duties':
            rows = (
                TeacherAssignment.objects.filter(status=TeacherAssignment.Status.ENDED)
                .select_related('teacher', 'subject', 'section', 'section__program', 'school_year')
                .order_by('-ended_at', '-created_at')
            )
            if year_id:
                rows = rows.filter(school_year_id=year_id)
            return Response(
                [
                    {
                        'id': row.id,
                        'teacher': row.teacher.get_full_name() or row.teacher.email,
                        'type': row.assignment_type,
                        'subject': row.subject.name if row.subject_id else '',
                        'section_id': row.section_id,
                        'section': section_label(row.section) if row.section_id else '',
                        'school_year': row.school_year.label,
                        'ended_at': row.ended_at,
                    }
                    for row in rows[:200]
                ]
            )
        rows = Section.objects.filter(archived_at__isnull=False).select_related('program', 'school_year')
        if year_id:
            rows = rows.filter(school_year_id=year_id)
        return Response(SectionSerializer(rows, many=True).data)
