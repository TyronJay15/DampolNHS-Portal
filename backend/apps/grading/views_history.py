from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.grading.advisory import section_subject_assignments
from apps.grading.models import Grade, GradeHistory
from apps.grading.recommend import recommend_payload
from apps.people.models import StudentSection, TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Section, Term


class GradeHistoryListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        rows = (
            GradeHistory.objects.select_related(
                'grade__student__user',
                'grade__subject',
                'grade__term',
                'grade__school_year',
                'grade__section',
                'changed_by',
            ).order_by('-changed_at')[:200]
        )
        return Response(
            [
                {
                    'id': row.id,
                    'student': row.grade.student.user.get_full_name(),
                    'lrn': row.grade.student.lrn,
                    'subject': row.grade.subject.name,
                    'term': row.grade.term.label,
                    'school_year': row.grade.school_year.label if row.grade.school_year_id else '',
                    'from_status': row.from_status,
                    'to_status': row.to_status,
                    'previous_score': str(row.previous_score) if row.previous_score is not None else '',
                    'new_score': str(row.new_score) if row.new_score is not None else '',
                    'changed_by': row.changed_by.get_full_name() if row.changed_by_id else '',
                    'duty': row.duty,
                    'reason': row.reason,
                    'changed_at': row.changed_at,
                }
                for row in rows
            ]
        )


class GradeReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        year = None
        year_id = request.query_params.get('school_year')
        if year_id:
            year = SchoolYear.objects.filter(pk=year_id).first()
        if year is None:
            year = SchoolYear.objects.filter(is_current=True).first()
        if year is None:
            return Response({'year': None, 'term': None, 'sections': []})

        term = None
        term_id = request.query_params.get('term')
        if term_id:
            term = Term.objects.filter(pk=term_id, school_year=year).first()
        if term is None:
            term = Term.objects.filter(school_year=year, is_current=True).first() or Term.objects.filter(
                school_year=year
            ).order_by('number').first()

        sections = Section.objects.filter(school_year=year, is_active=True).select_related('program')
        grade_level = (request.query_params.get('grade_level') or '').strip()
        program = (request.query_params.get('program') or '').strip().upper()
        if grade_level:
            sections = sections.filter(grade_level=grade_level)
        if program:
            sections = sections.filter(program__code=program)
        sections = sections.order_by('grade_level', 'program__code', 'name')

        payload = []
        for section in sections:
            subjects = section_subject_assignments(section)
            subject_ids = [row.subject_id for row in subjects]
            roster = list(
                StudentSection.objects.filter(section=section, school_year=year, is_active=True)
                .select_related('student', 'student__user')
                .order_by('student__user__last_name', 'student__user__first_name')
            )
            adviser = (
                TeacherAssignment.objects.filter(
                    section=section,
                    school_year=year,
                    assignment_type=TeacherAssignment.Type.ADVISER,
                    status=TeacherAssignment.Status.ACTIVE,
                )
                .select_related('teacher')
                .first()
            )
            grades = list(
                Grade.objects.filter(section=section, school_year=year, **({'term': term} if term else {})).select_related(
                    'subject'
                )
            )
            by_student = {}
            year_grades = {}
            for grade in grades:
                by_student.setdefault(grade.student_id, {})[grade.subject_id] = grade
            if term:
                released = Grade.objects.filter(
                    student_id__in=[row.student_id for row in roster],
                    school_year=year,
                    status__in=[Grade.Status.APPROVED, Grade.Status.RELEASED],
                ).select_related('subject')
                for grade in released:
                    year_grades.setdefault(grade.student_id, []).append(grade)

            students = []
            shown_count = 0
            for row in roster:
                scores = {}
                shown = True if subject_ids else False
                for subject_id in subject_ids:
                    grade = by_student.get(row.student_id, {}).get(subject_id)
                    scores[str(subject_id)] = {
                        'score': str(grade.score) if grade else '',
                        'status': grade.status if grade else '',
                    }
                    if not grade or grade.status != Grade.Status.RELEASED:
                        shown = False
                if shown:
                    shown_count += 1
                students.append(
                    {
                        'student_id': row.student_id,
                        'name': row.student.user.get_full_name(),
                        'lrn': row.student.lrn,
                        'shown': shown,
                        'scores': scores,
                        'recommendation': recommend_payload(year_grades.get(row.student_id, [])),
                    }
                )
            payload.append(
                {
                    'section_id': section.id,
                    'name': section.name,
                    'display_label': section_label(section),
                    'grade_level': section.grade_level,
                    'program_code': section.program.code if section.program_id else '',
                    'program_name': section.program.name if section.program_id else '',
                    'adviser': adviser.teacher.get_full_name() if adviser else '',
                    'student_count': len(roster),
                    'shown_count': shown_count,
                    'subjects': [{'id': row.subject_id, 'name': row.subject.name} for row in subjects],
                    'students': students,
                }
            )

        return Response(
            {
                'year': {'id': year.id, 'label': year.label},
                'term': {'id': term.id, 'label': term.label, 'number': term.number} if term else None,
                'sections': payload,
            }
        )
