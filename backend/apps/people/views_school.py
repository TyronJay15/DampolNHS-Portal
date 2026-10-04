from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import filter_levels, reading_levels, role_or_tagged
from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.people.assignments import DutyRejected, create_assignment
from apps.people.placement import (
    approved_registration,
    current_year,
    place_student,
    student_grade,
    student_program,
)
from apps.people.scope import require_grade_in_scope
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import Section
from apps.school.section_progress import recompute_status


PREPARE_PLACEMENTS = 'prepare_placements'
PREPARE_ASSIGNMENTS = 'prepare_assignments'


def _require_duty_in_scope(user, row):
    if row.section_id:
        require_grade_in_scope(user, row.section.grade_level)


class PlacementListView(APIView):
    """Head teachers place students; a teacher tagged to prepare placements reads the list in their levels."""

    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.HEAD_TEACHER, PREPARE_PLACEMENTS)]

    def get(self, request):
        year = current_year()
        profiles = (
            StudentProfile.objects.select_related('user')
            .filter(user__role=User.Role.STUDENT, user__approval_status=User.ApprovalStatus.APPROVED)
            .exclude(user__account_status__in=HIDDEN)
            .order_by('user__last_name', 'user__first_name')
        )
        assignments = {}
        if year:
            assignments = {
                row.student_id: row
                for row in StudentSection.objects.filter(is_active=True, school_year=year).select_related(
                    'section',
                    'section__program',
                )
            }
        rows = []
        for profile in profiles:
            registration = approved_registration(profile.user)
            placement = assignments.get(profile.id)
            program = student_program(profile, registration, placement)
            section = placement.section if placement else None
            rows.append(
                {
                    'student_id': profile.id,
                    'name': profile.user.get_full_name(),
                    'last_name': profile.user.last_name,
                    'first_name': profile.user.first_name,
                    'lrn': profile.lrn,
                    'gender': profile.gender,
                    'contact_number': profile.contact_number,
                    'grade_level': section.grade_level if section else student_grade(profile, registration),
                    'program_id': program.id if program else None,
                    'program_code': program.code if program else '',
                    'program_name': program.name if program else '',
                    'section_id': section.id if section else None,
                    'section': section_label(section) if section else '',
                    'placed': bool(section),
                }
            )
        scope = reading_levels(request.user, PREPARE_PLACEMENTS)
        if scope is not None:
            rows = [row for row in rows if row['grade_level'] in scope]
        rows.sort(
            key=lambda row: (
                0 if row['grade_level'] == 'Grade 11' else 1 if row['grade_level'] == 'Grade 12' else 2,
                row['program_code'] or 'zzz',
                (row['last_name'] or '').lower(),
                (row['first_name'] or '').lower(),
            )
        )
        return Response(rows)

    def post(self, request):
        year = current_year()
        if year is None:
            return Response({'detail': 'No current school year is set.'}, status=400)
        student = get_object_or_404(StudentProfile, pk=request.data.get('student'))
        section = get_object_or_404(
            Section,
            pk=request.data.get('section'),
            school_year=year,
            archived_at__isnull=True,
        )
        require_grade_in_scope(request.user, section.grade_level)
        error = place_student(
            student,
            section,
            year,
            request.user,
            transfer=bool(request.data.get('transfer')),
            override_capacity=bool(request.data.get('override_capacity')),
            reason=str(request.data.get('reason') or '').strip(),
        )
        if error:
            return Response({'detail': error}, status=400)
        return Response(
            {'student_id': student.id, 'section': section_label(section), 'section_id': section.id}
        )


class PlacementBulkView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request):
        year = current_year()
        if year is None:
            return Response({'detail': 'No current school year is set.'}, status=400)
        section = get_object_or_404(
            Section,
            pk=request.data.get('section'),
            school_year=year,
            archived_at__isnull=True,
        )
        require_grade_in_scope(request.user, section.grade_level)
        ids = request.data.get('students') or []
        override_capacity = bool(request.data.get('override_capacity'))
        reason = str(request.data.get('reason') or '').strip()
        placed = []
        failed = []
        for student_id in ids:
            student = get_object_or_404(StudentProfile, pk=student_id)
            error = place_student(
                student,
                section,
                year,
                request.user,
                override_capacity=override_capacity,
                reason=reason,
            )
            if error:
                failed.append({'student_id': student.id, 'name': student.user.get_full_name(), 'error': error})
                continue
            placed.append(student.id)
        if not placed and failed:
            return Response({'detail': failed[0]['error'], 'failed': failed}, status=400)
        return Response(
            {
                'section': section_label(section),
                'placed': len(placed),
                'failed': failed,
            }
        )


class TeacherStaffListView(APIView):
    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.HEAD_TEACHER, PREPARE_ASSIGNMENTS)]

    def get(self, request):
        rows = (
            User.objects.filter(role=User.Role.TEACHER)
            .exclude(account_status__in=HIDDEN)
            .order_by('last_name', 'first_name')
        )
        return Response(
            [
                {'id': row.id, 'name': row.get_full_name() or row.email, 'email': row.email}
                for row in rows
            ]
        )


class AssignmentAdminView(APIView):
    """Head teachers give duties; a teacher tagged to prepare assignments reads them in their levels."""

    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.HEAD_TEACHER, PREPARE_ASSIGNMENTS)]

    def get(self, request):
        rows = (
            TeacherAssignment.objects.filter(status=TeacherAssignment.Status.ACTIVE)
            .select_related('teacher', 'subject', 'section', 'section__program', 'school_year')
            .order_by('section__grade_level', 'section__name', 'teacher__last_name', 'subject__name')
        )
        rows = filter_levels(rows, reading_levels(request.user, PREPARE_ASSIGNMENTS), 'section__grade_level')
        return Response(
            [
                {
                    'id': row.id,
                    'teacher_id': row.teacher_id,
                    'teacher': row.teacher.get_full_name() or row.teacher.email,
                    'type': row.assignment_type,
                    'subject_id': row.subject_id,
                    'subject': row.subject.name if row.subject_id else '',
                    'section_id': row.section_id,
                    'section': section_label(row.section) if row.section_id else '',
                    'grade_level': row.section.grade_level if row.section_id else row.grade_level,
                    'program_code': row.section.program.code if row.section_id and row.section.program_id else '',
                    'school_year': row.school_year.label,
                }
                for row in rows
            ]
        )

    def post(self, request):
        try:
            payload = create_assignment(
                request.user,
                teacher_id=request.data.get('teacher'),
                assignment_type=request.data.get('type'),
                section_id=request.data.get('section'),
                subject_id=request.data.get('subject'),
                grade_level=request.data.get('grade_level', ''),
                reason=str(request.data.get('reason') or '').strip(),
            )
        except DutyRejected as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(payload, status=201)


class AssignmentAdminDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def delete(self, request, pk):
        row = get_object_or_404(
            TeacherAssignment.objects.select_related('teacher', 'subject', 'section'),
            pk=pk,
            status=TeacherAssignment.Status.ACTIVE,
        )
        _require_duty_in_scope(request.user, row)
        row.status = TeacherAssignment.Status.ENDED
        row.ended_at = timezone.now()
        row.save(update_fields=['status', 'ended_at'])
        if row.section_id:
            audit.record(
                user=request.user,
                action='assignment_ended',
                summary=f'Removed {row.teacher.get_full_name()} from {row.subject.name if row.subject_id else "adviser"} · {section_label(row.section)}',
                target_type='TeacherAssignment',
                target_id=row.id,
            )
            recompute_status(row.section)
        return Response({'id': row.id, 'status': row.status})

    def post(self, request, pk):
        row = get_object_or_404(
            TeacherAssignment.objects.select_related('section', 'section__school_year'),
            pk=pk,
            status=TeacherAssignment.Status.ENDED,
        )
        _require_duty_in_scope(request.user, row)
        if row.section_id and (row.section.archived_at or row.section.school_year.archived_at):
            return Response({'detail': 'Restore the section first.'}, status=400)
        if row.assignment_type == TeacherAssignment.Type.ADVISER and row.section_id:
            taken = TeacherAssignment.objects.filter(
                section=row.section,
                school_year=row.school_year,
                assignment_type=TeacherAssignment.Type.ADVISER,
                status=TeacherAssignment.Status.ACTIVE,
            ).exclude(pk=row.pk)
            if taken.exists():
                return Response({'detail': 'That section already has an adviser.'}, status=400)
        row.status = TeacherAssignment.Status.ACTIVE
        row.ended_at = None
        row.save(update_fields=['status', 'ended_at'])
        return Response({'id': row.id, 'status': row.status})


class AssignmentPurgeView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def post(self, request, pk):
        row = get_object_or_404(
            TeacherAssignment.objects.select_related('teacher', 'subject', 'section', 'school_year'),
            pk=pk,
            status=TeacherAssignment.Status.ENDED,
        )
        _require_duty_in_scope(request.user, row)
        label = (
            f'{row.teacher.get_full_name()} · {row.subject.name if row.subject_id else "Adviser"}'
            f' · {section_label(row.section) if row.section_id else row.school_year.label}'
        )
        row_id = row.id
        row.delete()
        audit.record(
            user=request.user,
            action='assignment_purged',
            summary=f'Permanently deleted duty {label}',
            target_type='TeacherAssignment',
            target_id=row_id,
        )
        return Response({'id': row_id, 'deleted': True})
