import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.people.models import TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section
from apps.school.serializers import SchoolYearSerializer, SectionSerializer

logger = logging.getLogger('apps.school')


def _year_busy(year):
    return year.sections.exists()


def _snapshot_archived_year(year):
    """Save that year's final Grade 11 counts. Called inside the archive transaction."""
    from apps.ml.forecast import snapshot_year

    snapshot_year(year)


def _retrain_forecast(user, year, archived):
    """Refit the enrollment trend after the year change has already been saved.

    A training failure must not undo the archive or restore. The planning page marks a stale model
    until the next successful retrain.
    """
    from apps.ml.forecast import retrain

    try:
        retrain(user, f'after {"archiving" if archived else "restoring"} {year.label}')
    except Exception:
        logger.exception(
            'Enrollment forecast was not retrained after %s school year %s.',
            'archiving' if archived else 'restoring',
            year.pk,
        )


class SchoolYearArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk, archived_at__isnull=True)
        if year.is_current:
            return Response({'detail': 'Make another year current before archiving this one.'}, status=400)
        with transaction.atomic():
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
            _snapshot_archived_year(year)
        _retrain_forecast(request.user, year, archived=True)
        return Response(SchoolYearSerializer(year).data)


class SchoolYearRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        year = get_object_or_404(SchoolYear, pk=pk)
        if year.archived_at is None:
            return Response({'detail': 'That year is already live.'}, status=400)
        with transaction.atomic():
            year_archived_at = year.archived_at
            year.archived_at = None
            year.save(update_fields=['archived_at'])
            from apps.school.section_progress import recompute_status

            for section in year.sections.filter(archived_at=year_archived_at):
                section.archived_at = None
                section.is_active = True
                section.save(update_fields=['archived_at', 'is_active'])
                recompute_status(section)
                ended = TeacherAssignment.objects.filter(
                    section=section,
                    school_year=year,
                    status=TeacherAssignment.Status.ENDED,
                    ended_at=year_archived_at,
                )
                for row in ended:
                    if row.assignment_type == TeacherAssignment.Type.ADVISER:
                        if TeacherAssignment.objects.filter(
                            section=section,
                            school_year=year,
                            assignment_type=TeacherAssignment.Type.ADVISER,
                            status=TeacherAssignment.Status.ACTIVE,
                        ).exists():
                            continue
                    elif row.subject_id:
                        if TeacherAssignment.objects.filter(
                            section=section,
                            school_year=year,
                            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
                            subject_id=row.subject_id,
                            status=TeacherAssignment.Status.ACTIVE,
                        ).exists():
                            continue
                    row.status = TeacherAssignment.Status.ACTIVE
                    row.ended_at = None
                    row.save(update_fields=['status', 'ended_at'])
            audit.record(
                user=request.user,
                action='school_year_restored',
                summary=f'Restored school year {year.label}',
                target_type='SchoolYear',
                target_id=year.id,
            )
        _retrain_forecast(request.user, year, archived=False)
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
        section.status = Section.Status.ARCHIVED
        section.save(update_fields=['archived_at', 'is_active', 'status'])
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
        archived_at = section.archived_at
        section.archived_at = None
        section.is_active = True
        from apps.school.section_progress import recompute_status

        recompute_status(section)
        ended = TeacherAssignment.objects.filter(
            section=section,
            school_year=section.school_year,
            status=TeacherAssignment.Status.ENDED,
            ended_at=archived_at,
        )
        for row in ended:
            if row.assignment_type == TeacherAssignment.Type.ADVISER:
                taken = TeacherAssignment.objects.filter(
                    section=section,
                    school_year=section.school_year,
                    assignment_type=TeacherAssignment.Type.ADVISER,
                    status=TeacherAssignment.Status.ACTIVE,
                ).exists()
                if taken:
                    continue
            elif row.subject_id:
                taken = TeacherAssignment.objects.filter(
                    section=section,
                    school_year=section.school_year,
                    assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
                    subject_id=row.subject_id,
                    status=TeacherAssignment.Status.ACTIVE,
                ).exists()
                if taken:
                    continue
            row.status = TeacherAssignment.Status.ACTIVE
            row.ended_at = None
            row.save(update_fields=['status', 'ended_at'])
        audit.record(
            user=request.user,
            action='section_restored',
            summary=f'Restored {section_label(section)}',
            target_type='Section',
            target_id=section.id,
        )
        return Response(SectionSerializer(section).data)


class ArchiveDeskView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        kind = (request.query_params.get('kind') or 'sections').strip()
        year_id = request.query_params.get('school_year')
        if kind == 'years':
            from apps.school.purge import year_delete_summary

            rows = SchoolYear.objects.filter(archived_at__isnull=False)
            payload = []
            for row in rows:
                data = SchoolYearSerializer(row).data
                summary = year_delete_summary(row)
                data['delete_summary'] = summary
                data['grades_protected'] = summary['grades'] > 0
                payload.append(data)
            return Response(payload)
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
        from apps.school.purge import section_delete_summary

        payload = []
        for row in rows:
            data = SectionSerializer(row).data
            summary = section_delete_summary(row)
            data['delete_summary'] = summary
            data['grades_protected'] = summary['grades'] > 0
            payload.append(data)
        return Response(payload)
