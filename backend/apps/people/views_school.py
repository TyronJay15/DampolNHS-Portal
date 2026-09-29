from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsHeadTeacher
from apps.audit import services as audit
from apps.audit.catalog import ASSIGNMENTS, PLACEMENT
from apps.notifications.services import advisers_for_section, head_teachers, notify
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section, Subject
from apps.school.offerings import program_offers_subject
from apps.school.section_progress import recompute_status


def _current_year():
    return SchoolYear.objects.filter(is_current=True, archived_at__isnull=True).first()


def _current_placement(student, year):
    return (
        StudentSection.objects.filter(student=student, school_year=year, is_active=True)
        .select_related('section', 'section__program', 'section__school_year')
        .first()
    )


def _notify_placement(student, old_section, section, transfer):
    name = student.user.get_full_name() or student.lrn
    label = section_label(section)
    if transfer and old_section:
        notify(
            advisers_for_section(old_section) + advisers_for_section(section),
            title='Roster change · transfer',
            body=f'{name} moved from {section_label(old_section)} to {label}.',
            category=PLACEMENT,
            action_path='/teacher/advisory',
        )
        return
    notify(
        advisers_for_section(section),
        title='Roster change · placement',
        body=f'{name} was placed in {label}.',
        category=PLACEMENT,
        action_path='/teacher/advisory',
    )


def _section_count(section):
    return section.student_assignments.filter(is_active=True).count()


def _capacity_error(section, incoming=1, override=False):
    if not section.capacity:
        return None
    count = _section_count(section)
    if count + incoming > section.capacity and not override:
        return (
            f'This section is at capacity ({count}/{section.capacity}). '
            'Confirm to exceed the limit.'
        )
    return None


def _place_student(student, section, year, user, transfer=False, override_capacity=False, reason=''):
    if student.user.account_status in HIDDEN:
        return 'That student account is archived.'
    registration = _approved_registration(student.user)
    if (
        not transfer
        and registration
        and section.program_id
        and registration.program_id != section.program_id
    ):
        return 'Place the student in a section of their enrolled program.'
    student_grade = _student_grade(student, registration)
    if student_grade and section.grade_level and student_grade != section.grade_level:
        return 'Place the student in a section of their grade level.'
    if section.archived_at or section.school_year.archived_at:
        return 'That section is archived.'
    current = _current_placement(student, year)
    old_section = current.section if current else None
    if old_section and old_section.id == section.id:
        return None
    if not old_section:
        cap_error = _capacity_error(section, override=override_capacity)
        if cap_error:
            return cap_error
    StudentSection.objects.filter(student=student, school_year=year, is_active=True).update(
        is_active=False,
        ended_at=timezone.now(),
    )
    StudentSection.objects.create(
        student=student,
        section=section,
        school_year=year,
        assigned_by=user,
    )
    name = student.user.get_full_name() or student.lrn
    label = section_label(section)
    if transfer or old_section:
        audit.record(
            user=user,
            action='student_transferred',
            summary=f'Transferred {name} to {label}',
            target_type='StudentSection',
            target_id=student.id,
            details={
                'student': name,
                'from': section_label(old_section) if old_section else '',
                'to': label,
                'reason': reason,
            },
        )
        notify(
            head_teachers(),
            title='Roster change · transfer',
            body=f'{name} was transferred to {label}.',
            level='info',
            category=PLACEMENT,
            action_path=f'/head/sections/{section.id}/setup?step=students',
        )
    else:
        audit.record(
            user=user,
            action='student_placed',
            summary=f'Placed {name} in {label}',
            target_type='StudentSection',
            target_id=student.id,
            details={'student': name, 'section': label, 'reason': reason},
        )
    _notify_placement(student, old_section, section, transfer or bool(old_section))
    recompute_status(section)
    if old_section and old_section.id != section.id:
        recompute_status(old_section)
    return None


def _approved_registration(user):
    return (
        Registration.objects.filter(user=user, status=Registration.Status.APPROVED)
        .select_related('program')
        .first()
    )


def _student_grade(profile, registration):
    return profile.grade_level or (registration.grade_level_enrollment if registration else '')


def _student_program(profile, registration, placement=None):
    if placement and placement.section and placement.section.program_id:
        return placement.section.program
    if registration:
        return registration.program
    return None


class PlacementListView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        year = _current_year()
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
            registration = _approved_registration(profile.user)
            placement = assignments.get(profile.id)
            program = _student_program(profile, registration, placement)
            section = placement.section if placement else None
            rows.append(
                {
                    'student_id': profile.id,
                    'name': profile.user.get_full_name(),
                    'last_name': profile.user.last_name,
                    'first_name': profile.user.first_name,
                    'lrn': profile.lrn,
                    'contact_number': profile.contact_number,
                    'grade_level': section.grade_level if section else _student_grade(profile, registration),
                    'program_id': program.id if program else None,
                    'program_code': program.code if program else '',
                    'program_name': program.name if program else '',
                    'section_id': section.id if section else None,
                    'section': section_label(section) if section else '',
                    'placed': bool(section),
                }
            )
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
        year = _current_year()
        if year is None:
            return Response({'detail': 'No current school year is set.'}, status=400)
        student = get_object_or_404(StudentProfile, pk=request.data.get('student'))
        section = get_object_or_404(
            Section,
            pk=request.data.get('section'),
            school_year=year,
            archived_at__isnull=True,
        )
        error = _place_student(
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
        year = _current_year()
        if year is None:
            return Response({'detail': 'No current school year is set.'}, status=400)
        section = get_object_or_404(
            Section,
            pk=request.data.get('section'),
            school_year=year,
            archived_at__isnull=True,
        )
        ids = request.data.get('students') or []
        override_capacity = bool(request.data.get('override_capacity'))
        reason = str(request.data.get('reason') or '').strip()
        placed = []
        failed = []
        for student_id in ids:
            student = get_object_or_404(StudentProfile, pk=student_id)
            error = _place_student(
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
    permission_classes = [IsAuthenticated, IsHeadTeacher]

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
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def get(self, request):
        rows = (
            TeacherAssignment.objects.filter(status=TeacherAssignment.Status.ACTIVE)
            .select_related('teacher', 'subject', 'section', 'section__program', 'school_year')
            .order_by('section__grade_level', 'section__name', 'teacher__last_name', 'subject__name')
        )
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
        year = _current_year()
        if year is None:
            return Response({'detail': 'No current school year is set.'}, status=400)
        teacher = get_object_or_404(User, pk=request.data.get('teacher'), role=User.Role.TEACHER)
        if teacher.account_status in HIDDEN:
            return Response({'detail': 'That teacher account is archived.'}, status=400)
        assignment_type = request.data.get('type') or TeacherAssignment.Type.SUBJECT_TEACHER
        allowed = {TeacherAssignment.Type.SUBJECT_TEACHER, TeacherAssignment.Type.ADVISER}
        if assignment_type not in allowed:
            return Response({'detail': 'Choose subject teacher or adviser.'}, status=400)
        section = None
        subject = None
        if request.data.get('section'):
            section = get_object_or_404(Section, pk=request.data.get('section'), archived_at__isnull=True)
            if section.school_year.archived_at:
                return Response({'detail': 'That section is archived.'}, status=400)
        if request.data.get('subject'):
            subject = get_object_or_404(Subject, pk=request.data.get('subject'))
        if assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER and (not section or not subject):
            return Response({'detail': 'Subject teachers need a section and a subject.'}, status=400)
        if assignment_type == TeacherAssignment.Type.ADVISER and not section:
            return Response({'detail': 'Advisers need a section.'}, status=400)
        if (
            assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER
            and section
            and section.program_id
            and subject
            and not program_offers_subject(section.program, subject)
        ):
            return Response(
                {'detail': f'{subject.name} is not a {section.program.code} subject.'},
                status=400,
            )
        previous = None
        if assignment_type == TeacherAssignment.Type.ADVISER and section:
            previous = TeacherAssignment.objects.filter(
                section=section,
                school_year=year,
                assignment_type=TeacherAssignment.Type.ADVISER,
                status=TeacherAssignment.Status.ACTIVE,
            ).select_related('teacher').first()
            if previous:
                previous.status = TeacherAssignment.Status.ENDED
                previous.ended_at = timezone.now()
                previous.save(update_fields=['status', 'ended_at'])
        if assignment_type == TeacherAssignment.Type.SUBJECT_TEACHER and section and subject:
            previous = TeacherAssignment.objects.filter(
                section=section,
                school_year=year,
                assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
                subject=subject,
                status=TeacherAssignment.Status.ACTIVE,
            ).select_related('teacher').first()
            if previous:
                previous.status = TeacherAssignment.Status.ENDED
                previous.ended_at = timezone.now()
                previous.save(update_fields=['status', 'ended_at'])
        try:
            row = TeacherAssignment.objects.create(
                teacher=teacher,
                assignment_type=assignment_type,
                school_year=year,
                section=section,
                subject=subject,
                grade_level=section.grade_level if section else request.data.get('grade_level', ''),
                assigned_by=request.user,
            )
        except IntegrityError:
            if assignment_type == TeacherAssignment.Type.ADVISER:
                return Response({'detail': 'That section already has an adviser.'}, status=400)
            return Response({'detail': 'That teacher already has this duty.'}, status=400)
        reason = str(request.data.get('reason') or '').strip()
        label = section_label(section) if section else ''
        teacher_name = teacher.get_full_name() or teacher.email
        if assignment_type == TeacherAssignment.Type.ADVISER:
            audit.record(
                user=request.user,
                action='adviser_assigned',
                summary=f'Assigned {teacher_name} as adviser for {label}',
                target_type='TeacherAssignment',
                target_id=row.id,
                details={
                    'previous': (
                        previous.teacher.get_full_name() or previous.teacher.email if previous else ''
                    ),
                    'new': teacher_name,
                    'reason': reason,
                },
            )
            notify(
                [teacher],
                title='Adviser assignment',
                body=f'You are now adviser for {label}.',
                level='info',
                category=ASSIGNMENTS,
                action_path='/teacher/advisory',
            )
        else:
            audit.record(
                user=request.user,
                action='subject_teacher_assigned',
                summary=f'Assigned {teacher_name} to {subject.name} · {label}',
                target_type='TeacherAssignment',
                target_id=row.id,
                details={
                    'subject': subject.name if subject else '',
                    'previous': (
                        previous.teacher.get_full_name() or previous.teacher.email if previous else ''
                    ),
                    'new': teacher_name,
                    'reason': reason,
                },
            )
            notify(
                [teacher],
                title='Subject assignment',
                body=f'You are assigned to {subject.name} · {label}.',
                level='info',
                category=ASSIGNMENTS,
                action_path='/teacher/classes',
            )
        if section:
            recompute_status(section)
        return Response(
            {
                'id': row.id,
                'teacher': teacher_name,
                'type': row.assignment_type,
                'section': label,
                'subject': subject.name if subject else '',
            },
            status=201,
        )


class AssignmentAdminDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def delete(self, request, pk):
        row = get_object_or_404(
            TeacherAssignment.objects.select_related('teacher', 'subject', 'section'),
            pk=pk,
            status=TeacherAssignment.Status.ACTIVE,
        )
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
