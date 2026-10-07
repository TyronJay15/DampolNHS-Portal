"""Printable grade records of the signed-in staff member. Read-only.

GET /api/grades/print/records/?school_year=<id>&term=<id>
  teacher       the grade sheets of every class they teach in that year, one group per section and subject
  head teacher  every grade decision they made (approve, return, correction) in that year

The report only covers the requester's own work, so no extra scope check is needed beyond the role.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.throttles import ScopedThrottle
from apps.grading.models import Grade, GradeHistory
from apps.grading.views_print import school_name
from apps.people.models import TeacherAssignment
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Term

TEACHER_COLUMNS = [
    {'key': 'term', 'label': 'Term'},
    {'key': 'student', 'label': 'Learner'},
    {'key': 'lrn', 'label': 'LRN'},
    {'key': 'grade', 'label': 'Grade', 'num': True},
    {'key': 'status', 'label': 'Status'},
]
HEAD_COLUMNS = [
    {'key': 'when', 'label': 'Date'},
    {'key': 'student', 'label': 'Learner'},
    {'key': 'class', 'label': 'Section · Subject'},
    {'key': 'term', 'label': 'Term'},
    {'key': 'change', 'label': 'Change'},
    {'key': 'reason', 'label': 'Action'},
]


def _teacher_groups(user, year, term):
    duties = (
        TeacherAssignment.objects.filter(
            teacher=user,
            school_year=year,
            assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
            section__isnull=False,
            subject__isnull=False,
        )
        .select_related('section', 'section__program', 'subject')
        .order_by('section__name', 'subject__name')
    )
    groups = []
    for duty in duties:
        grades = Grade.objects.filter(section=duty.section, subject=duty.subject, school_year=year).select_related(
            'student__user', 'term'
        )
        if term:
            grades = grades.filter(term=term)
        rows = [
            {
                'term': grade.term.label,
                'student': grade.student.user.get_full_name(),
                'lrn': grade.student.lrn,
                'grade': str(grade.score),
                'status': grade.get_status_display(),
            }
            for grade in grades.order_by('term__number', 'student__user__last_name', 'student__user__first_name')
        ]
        groups.append({'title': f'{duty.subject.name} · {section_label(duty.section)}', 'rows': rows})
    return groups


def _class_label(grade):
    section = section_label(grade.section) if grade.section_id else ''
    return f'{section} · {grade.subject.name}' if section else grade.subject.name


def _head_groups(user, year, term):
    entries = (
        GradeHistory.objects.filter(changed_by=user, grade__school_year=year)
        .select_related('grade__student__user', 'grade__subject', 'grade__section', 'grade__term')
        .order_by('-changed_at')
    )
    if term:
        entries = entries.filter(grade__term=term)
    rows = [
        {
            'when': timezone.localtime(entry.changed_at).strftime('%b %d, %Y'),
            'student': entry.grade.student.user.get_full_name(),
            'class': _class_label(entry.grade),
            'term': entry.grade.term.label,
            'change': f'{entry.from_status or "new"} → {entry.to_status}',
            'reason': entry.reason,
        }
        for entry in entries
    ]
    return [{'title': 'Grade decisions', 'rows': rows}]


class GradeRecordsPrintView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'reports'  # heavy queries: repeated calls must not stall the server for everyone

    def get(self, request):
        user = request.user
        if user.role not in (User.Role.TEACHER, User.Role.HEAD_TEACHER):
            raise PermissionDenied('Only teachers and head teachers have grade records to print.')
        year_id = request.query_params.get('school_year')
        year = (
            get_object_or_404(SchoolYear, pk=year_id)
            if year_id
            else SchoolYear.objects.filter(is_current=True).first()
        )
        if year is None:
            return Response({'detail': 'There is no current school year yet.'}, status=400)
        term = None
        if request.query_params.get('term'):
            term = get_object_or_404(Term, pk=request.query_params['term'], school_year=year)

        is_teacher = user.role == User.Role.TEACHER
        groups = _teacher_groups(user, year, term) if is_teacher else _head_groups(user, year, term)
        return Response(
            {
                'school': school_name(),
                'title': 'Class Grade Records' if is_teacher else 'Grade Decision Records',
                'generated_at': timezone.localtime(),
                'person': {'name': user.get_full_name() or user.email, 'role': user.get_role_display()},
                'school_year': year.label,
                'term': term.label if term else 'All terms',
                'terms': [{'id': row.id, 'label': row.label} for row in Term.objects.filter(school_year=year)],
                'columns': TEACHER_COLUMNS if is_teacher else HEAD_COLUMNS,
                'groups': groups,
                'total': sum(len(group['rows']) for group in groups),
            }
        )
