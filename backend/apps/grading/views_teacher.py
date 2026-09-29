from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile
from apps.accounts.permissions import IsTeacher
from apps.audit import services as audit
from apps.grading.history import SUBJECT_TEACHER, write_history
from apps.grading.models import CorrectionRequest, Grade, GradeHistory
from apps.grading.progress import pack_counts
from apps.grading.scores import parse_score
from apps.grading.transitions import transition_grades
from apps.audit.catalog import GRADES
from apps.notifications.services import advisers_for_section, head_teachers, notify
from apps.people.assignment_access import subject_assignment_for
from apps.people.models import StudentSection
from apps.school.deadlines import encode_closed_response, encode_is_open
from apps.school.labels import section_label
from apps.school.models import Term

EDITABLE = {Grade.Status.DRAFT}

class TeacherClassGradesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        assignment = subject_assignment_for(request.user, request.query_params.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You cannot encode grades for that class.'}, status=403)

        term = get_object_or_404(Term, pk=request.query_params.get('term'), school_year=assignment.school_year)
        roster = (
            StudentSection.objects.filter(
                section=assignment.section,
                school_year=assignment.school_year,
                is_active=True,
            ).exclude(student__user__account_status__in=HIDDEN)
            .select_related('student', 'student__user')
            .order_by('student__user__last_name', 'student__user__first_name')
        )
        grades = {
            row.student_id: row
            for row in Grade.objects.filter(
                subject=assignment.subject,
                term=term,
                student_id__in=[item.student_id for item in roster],
            )
        }
        pending = set(
            CorrectionRequest.objects.filter(
                grade_id__in=[row.id for row in grades.values()],
                status=CorrectionRequest.Status.PENDING,
            ).values_list('grade_id', flat=True)
        )
        students = [_row_payload(item.student, grades.get(item.student_id), pending) for item in roster]
        draft = submitted = approved = released = 0
        for row in students:
            if row['status'] == Grade.Status.DRAFT:
                draft += 1
            elif row['status'] == Grade.Status.SUBMITTED:
                submitted += 1
            elif row['status'] == Grade.Status.APPROVED:
                approved += 1
            elif row['status'] == Grade.Status.RELEASED:
                released += 1
        return Response(
            {
                'assignment': {
                    'id': assignment.id,
                    'section': section_label(assignment.section),
                    'section_label': section_label(assignment.section),
                    'subject': assignment.subject.name,
                    'school_year': assignment.school_year.label,
                },
                'term': {
                    'id': term.id,
                    'label': term.label,
                    'number': term.number,
                    'encode_opens_at': term.encode_opens_at,
                    'encode_closes_at': term.encode_closes_at,
                    'encode_open': encode_is_open(term),
                },
                'summary': pack_counts(len(students), draft=draft, submitted=submitted, approved=approved, released=released),
                'students': students,
            }
        )


class TeacherEncodeGradeView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        assignment = subject_assignment_for(request.user, request.data.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You cannot encode grades for that class.'}, status=403)

        term = get_object_or_404(Term, pk=request.data.get('term'), school_year=assignment.school_year)
        if not encode_is_open(term):
            return Response(encode_closed_response(term), status=400)
        student = get_object_or_404(StudentProfile.objects.select_related('user'), pk=request.data.get('student'))
        if not StudentSection.objects.filter(
            student=student,
            section=assignment.section,
            school_year=assignment.school_year,
            is_active=True,
        ).exists():
            return Response({'detail': 'That student is not in this class.'}, status=400)

        score = parse_score(request.data.get('score'))
        if score is None:
            return Response({'detail': 'Enter a grade from 0 to 100.'}, status=400)

        with transaction.atomic():
            grade, created = Grade.objects.select_for_update().get_or_create(
                student=student,
                subject=assignment.subject,
                term=term,
                defaults={
                    'school_year': assignment.school_year,
                    'section': assignment.section,
                    'teacher': request.user,
                    'score': score,
                    'status': Grade.Status.DRAFT,
                    'updated_by': request.user,
                },
            )
            if not created:
                if grade.status not in EDITABLE:
                    return Response(
                        {'detail': 'This grade is submitted, approved, or released and cannot be changed here.'},
                        status=400,
                    )
                previous = grade.score
                grade.score = score
                grade.section = assignment.section
                grade.teacher = request.user
                grade.updated_by = request.user
                grade.save(update_fields=['score', 'section', 'teacher', 'updated_by', 'updated_at'])
                write_history(
                    grade=grade,
                    from_status=grade.status,
                    to_status=grade.status,
                    previous_score=previous,
                    new_score=score,
                    user=request.user,
                    reason='Teacher encoded grade',
                    duty=SUBJECT_TEACHER,
                )
            else:
                write_history(
                    grade=grade,
                    from_status='',
                    to_status=Grade.Status.DRAFT,
                    previous_score=None,
                    new_score=score,
                    user=request.user,
                    reason='Teacher encoded grade',
                    duty=SUBJECT_TEACHER,
                )
        return Response(_row_payload(student, grade))


class TeacherSubmitClassView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        assignment = subject_assignment_for(request.user, request.data.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You cannot submit grades for that class.'}, status=403)

        term = get_object_or_404(Term, pk=request.data.get('term'), school_year=assignment.school_year)
        if not encode_is_open(term):
            return Response(encode_closed_response(term), status=400)
        drafts = Grade.objects.filter(
            subject=assignment.subject,
            section=assignment.section,
            term=term,
            status=Grade.Status.DRAFT,
        )
        moved = transition_grades(
            grades=list(drafts),
            to_status=Grade.Status.SUBMITTED,
            user=request.user,
            reason='Teacher submitted class grades',
            duty=SUBJECT_TEACHER,
        )
        audit.record(
            user=request.user,
            action='grades_submitted',
            summary=f'Submitted {moved} {assignment.subject.name} grade(s) for {assignment.section.name}',
            target_type='Section',
            target_id=assignment.section_id,
            details={'term': term.id, 'subject': assignment.subject_id, 'submitted': moved},
        )
        if moved:
            notify(
                head_teachers(),
                title=f'{term.label} · {assignment.subject.name} submitted',
                body=f'{request.user.get_full_name()} submitted grades for {section_label(assignment.section)}.',
                category=GRADES,
                action_path='/head/approve',
            )
            if Grade.objects.filter(
                section=assignment.section,
                term=term,
                status=Grade.Status.RELEASED,
            ).exists():
                notify(
                    advisers_for_section(assignment.section),
                    title=f'{term.label} · submitted for a shown card',
                    body=(
                        f'{request.user.get_full_name()} submitted {assignment.subject.name} for '
                        f'{section_label(assignment.section)}. Waiting for Head Teacher approval before you can re-show.'
                    ),
                    level='info',
                    category=GRADES,
                    action_path='/teacher/advisory',
                )
        return Response({'submitted': moved})


def _row_payload(student, grade, pending=None):
    pending = pending or set()
    return {
        'student_id': student.id,
        'name': student.user.get_full_name(),
        'lrn': student.lrn,
        'grade_id': grade.id if grade else None,
        'score': str(grade.score) if grade else '',
        'status': grade.status if grade else '',
        'editable': grade is None or grade.status in EDITABLE,
        'can_correct': bool(grade and grade.status not in EDITABLE),
        'correction_pending': bool(grade and grade.id in pending),
        'updated_at': grade.updated_at if grade else None,
    }


class TeacherGradeTimelineView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        assignment = subject_assignment_for(request.user, request.query_params.get('assignment'))
        if assignment is None:
            return Response({'detail': 'You cannot view that class.'}, status=403)
        term = get_object_or_404(Term, pk=request.query_params.get('term'), school_year=assignment.school_year)
        student = get_object_or_404(StudentProfile, pk=request.query_params.get('student'))
        grade = Grade.objects.filter(
            student=student,
            subject=assignment.subject,
            term=term,
            section=assignment.section,
        ).first()
        if grade is None:
            return Response({'events': []})
        return Response(
            {
                'events': [
                    {
                        'id': row.id,
                        'from_status': row.from_status,
                        'to_status': row.to_status,
                        'previous_score': str(row.previous_score) if row.previous_score is not None else '',
                        'new_score': str(row.new_score) if row.new_score is not None else '',
                        'changed_by': row.changed_by.get_full_name() if row.changed_by_id else '',
                        'duty': row.duty,
                        'reason': row.reason,
                        'changed_at': row.changed_at,
                    }
                    for row in GradeHistory.objects.filter(grade=grade).order_by('changed_at')
                ]
            }
        )
