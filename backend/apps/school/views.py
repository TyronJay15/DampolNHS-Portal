from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import IsAdminOrHeadTeacher, IsHeadTeacher, IsStaffUser
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.notifications.services import notify, teachers_for_year
from apps.school.models import Program, SchoolYear, Section, Subject, Term
from apps.school.serializers import (
    ProgramSerializer,
    SchoolYearSerializer,
    SectionSerializer,
    SubjectSerializer,
    TermSerializer,
)


class ProgramViewSet(ReadOnlyModelViewSet):
    serializer_class = ProgramSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None
    queryset = Program.objects.filter(is_active=True).prefetch_related(
        'program_subjects__subject',
    )


class SchoolYearViewSet(ModelViewSet):
    serializer_class = SchoolYearSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        if self.request.query_params.get('archived'):
            return SchoolYear.objects.filter(archived_at__isnull=False)
        return SchoolYear.objects.filter(archived_at__isnull=True)

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrHeadTeacher()]

    def perform_create(self, serializer):
        year = serializer.save()
        for number in (1, 2, 3):
            Term.objects.get_or_create(
                school_year=year,
                number=number,
                defaults={'label': f'Term {number}'},
            )
        audit.record(
            user=self.request.user,
            action='school_year_created',
            summary=f'Opened school year {year.label}',
            target_type='SchoolYear',
            target_id=year.id,
            details={'label': year.label, 'is_current': year.is_current},
        )


class TermViewSet(ModelViewSet):
    serializer_class = TermSerializer
    pagination_class = None
    http_method_names = ['get', 'patch', 'head', 'options']
    queryset = Term.objects.select_related('school_year')
    filterset_fields = ['school_year', 'number', 'status']

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), IsStaffUser()]
        return [IsAuthenticated(), IsHeadTeacher()]

    def perform_update(self, serializer):
        previous_open = serializer.instance.encode_opens_at
        previous_close = serializer.instance.encode_closes_at
        term = serializer.save()
        audit.record(
            user=self.request.user,
            action='deadline_set',
            summary=f'Set encode window for {term.label}',
            target_type='Term',
            target_id=term.id,
            details={
                'term_label': term.label,
                'encode_opens_at': term.encode_opens_at.isoformat() if term.encode_opens_at else None,
                'encode_closes_at': term.encode_closes_at.isoformat() if term.encode_closes_at else None,
                'previous_opens_at': previous_open.isoformat() if previous_open else None,
                'previous_closes_at': previous_close.isoformat() if previous_close else None,
            },
        )
        if term.encode_closes_at and term.encode_closes_at != previous_close:
            when = timezone.localtime(term.encode_closes_at).strftime('%b %d, %Y')
            from apps.audit.catalog import SCHOOL

            notify(
                teachers_for_year(term.school_year),
                title=f'{term.label} encode window',
                body=f'Encode {term.label} grades by {when}. Submit the class when the table is ready.',
                category=SCHOOL,
                action_path='/teacher/classes',
            )


class EncodeWindowHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        year_id = request.query_params.get('school_year')
        year = (
            SchoolYear.objects.filter(pk=year_id).first()
            if year_id
            else SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()
        )
        if year is None:
            return Response([])
        terms = {str(row.id): row for row in Term.objects.filter(school_year=year)}
        logs = AuditLog.objects.filter(
            action='deadline_set',
            target_type='Term',
            target_id__in=terms.keys(),
        ).order_by('-created_at')
        return Response(
            [
                {
                    'id': row.id,
                    'term': terms[row.target_id].label,
                    'opens_at': row.details.get('encode_opens_at'),
                    'closes_at': row.details.get('encode_closes_at'),
                    'changed_by': row.actor_label,
                    'changed_at': row.created_at,
                }
                for row in logs
            ]
        )


class SubjectViewSet(ReadOnlyModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]
    pagination_class = None

    def get_queryset(self):
        queryset = Subject.objects.filter(is_active=True)
        program = self.request.query_params.get('program')
        if not program:
            return queryset
        if str(program).isdigit():
            queryset = queryset.filter(program_links__program_id=program)
        else:
            queryset = queryset.filter(program_links__program__code=str(program).upper())
        return queryset.distinct()


class SectionViewSet(ModelViewSet):
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, IsHeadTeacher]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        rows = Section.objects.select_related('school_year', 'program')
        school_year = self.request.query_params.get('school_year')
        status = self.request.query_params.get('status')
        grade_level = self.request.query_params.get('grade_level')
        program = self.request.query_params.get('program')
        if self.request.query_params.get('archived'):
            rows = rows.filter(archived_at__isnull=False)
        else:
            rows = rows.filter(archived_at__isnull=True, school_year__archived_at__isnull=True)
        if school_year:
            rows = rows.filter(school_year_id=school_year)
        if status:
            rows = rows.filter(status=status)
        if grade_level:
            rows = rows.filter(grade_level=grade_level)
        if program:
            if str(program).isdigit():
                rows = rows.filter(program_id=program)
            else:
                rows = rows.filter(program__code=str(program).upper())
        return rows

    def perform_create(self, serializer):
        section = serializer.save(status=Section.Status.DRAFT)
        audit.record(
            user=self.request.user,
            action='section_created',
            summary=f'Created {section.name} for {section.school_year.label}',
            target_type='Section',
            target_id=section.id,
            details={'grade_level': section.grade_level, 'program': section.program.code if section.program_id else ''},
        )

    def perform_update(self, serializer):
        section = serializer.save()
        if section.status != Section.Status.ACTIVE and not section.archived_at:
            from apps.school.section_progress import recompute_status

            recompute_status(section)

    def destroy(self, request, *args, **kwargs):
        section = self.get_object()
        if section.student_assignments.exists() or section.teacher_assignments.exists():
            return Response({'detail': 'Remove or archive a section that has students or duties.'}, status=400)
        from apps.grading.models import Grade

        if Grade.objects.filter(section=section).exists():
            return Response({'detail': 'Archive a section that has grades.'}, status=400)
        if not section.archived_at and section.status == Section.Status.ACTIVE:
            return Response({'detail': 'Archive this section before deleting it.'}, status=400)
        label = section.name
        section_id = section.id
        section.delete()
        audit.record(
            user=request.user,
            action='section_deleted',
            summary=f'Deleted section {label}',
            target_type='Section',
            target_id=section_id,
        )
        return Response(status=204)
