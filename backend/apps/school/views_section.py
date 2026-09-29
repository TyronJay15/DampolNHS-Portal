from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.audit.catalog import ASSIGNMENTS
from apps.notifications.services import notify
from apps.school.labels import section_label
from apps.school.models import Section
from apps.school.section_progress import activation_checks, recompute_status, section_progress
from apps.school.serializers import SectionSerializer


def teachers_for_section_assignments(section):
    from apps.people.models import TeacherAssignment

    ids = TeacherAssignment.objects.filter(
        section=section,
        school_year=section.school_year,
        status=TeacherAssignment.Status.ACTIVE,
    ).values_list('teacher_id', flat=True)
    from apps.accounts.models import User

    return list(User.objects.filter(id__in=ids))


class SectionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request, pk):
        section = get_object_or_404(
            Section.objects.select_related('school_year', 'program'),
            pk=pk,
        )
        payload = SectionSerializer(section).data
        payload['progress'] = section_progress(section)
        payload['activation'] = activation_checks(section)
        payload['identity_locked'] = section.status == Section.Status.ACTIVE or bool(section.archived_at)
        return Response(payload)


class SectionActivateView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        section = get_object_or_404(
            Section.objects.select_related('school_year', 'program'),
            pk=pk,
            archived_at__isnull=True,
        )
        if section.status == Section.Status.ACTIVE:
            return Response({'detail': 'This section is already active.'}, status=400)
        validation = activation_checks(section)
        allow_incomplete = bool(request.data.get('allow_incomplete'))
        if not validation['can_activate'] and not allow_incomplete:
            return Response(
                {
                    'detail': 'Section cannot be activated yet.',
                    'blocked': validation['blocked'],
                    'checks': validation['checks'],
                },
                status=400,
            )
        section.status = Section.Status.ACTIVE
        section.is_active = True
        section.save(update_fields=['status', 'is_active'])
        label = section_label(section)
        reason = str(request.data.get('reason') or '').strip()
        audit.record(
            user=request.user,
            action='section_activated_incomplete' if allow_incomplete and not validation['can_activate'] else 'section_activated',
            summary=f'Activated {label}' + (' (incomplete setup)' if allow_incomplete and not validation['can_activate'] else ''),
            target_type='Section',
            target_id=section.id,
            details={
                'allow_incomplete': allow_incomplete,
                'blocked': validation['blocked'],
                'reason': reason,
            },
        )
        teachers = teachers_for_section_assignments(section)
        if teachers:
            notify(
                teachers,
                title='Section assignment live',
                body=f'{label} is active. Your assigned classes are ready.',
                level='info',
                category=ASSIGNMENTS,
                action_path='/teacher/classes',
            )
        payload = SectionSerializer(section).data
        payload['progress'] = section_progress(section)
        return Response(payload)
