from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsHeadTeacher
from apps.notifications.services import advisers_for_section, notify
from apps.people.models import Registration, StudentSection, TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section, Subject
from apps.school.offerings import program_offers_subject


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
    if transfer and old_section:
        notify(
            advisers_for_section(old_section) + advisers_for_section(section),
            title='Student transferred',
            body=f'{name} moved from {section_label(old_section)} to {section_label(section)}.',
        )
        return
    notify(
        advisers_for_section(section),
        title='Student placed',
        body=f'{name} was placed in {section_label(section)}.',
    )


def _place_student(student, section, year, user, transfer=False):
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
    _notify_placement(student, old_section, section, transfer or bool(old_section))
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
        placed = []
        for student_id in ids:
            student = get_object_or_404(StudentProfile, pk=student_id)
            error = _place_student(student, section, year, request.user)
            if error:
                return Response({'detail': error}, status=400)
            placed.append(student.id)
        return Response({'section': section_label(section), 'placed': len(placed)})


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
        return Response(
            {
                'id': row.id,
                'teacher': teacher.get_full_name() or teacher.email,
                'type': row.assignment_type,
                'section': section_label(section) if section else '',
                'subject': subject.name if subject else '',
            },
            status=201,
        )


class AssignmentAdminDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHeadTeacher]

    def delete(self, request, pk):
        row = get_object_or_404(TeacherAssignment, pk=pk, status=TeacherAssignment.Status.ACTIVE)
        row.status = TeacherAssignment.Status.ENDED
        row.ended_at = timezone.now()
        row.save(update_fields=['status', 'ended_at'])
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
