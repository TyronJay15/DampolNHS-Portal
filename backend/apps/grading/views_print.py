"""Printable grade report data. Read-only: it never changes a grade, its status or any approval.

GET /api/grades/print/?student=<profile id>&school_year=<id>&term=<id>
Who may read which grades is decided here on the server, not by the button that links to it:
  student       own released grades only
  teacher       adviser of the student's section: every subject; subject teacher: only their own subject
  head teacher  students in the grade levels they are assigned to (whole school if none are assigned)
  admin         any student
Staff reports include approved and released grades; a student sees only what was released to them.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile, User
from apps.accounts.throttles import ScopedThrottle
from apps.cms.models import SiteContent
from apps.grading.models import Grade
from apps.grading.scores import average
from apps.people.models import StudentSection, TeacherAssignment
from apps.people.scope import grade_in_scope
from apps.school.labels import section_label
from apps.school.models import SchoolYear, Term

PASSING_SCORE = 75
DEFAULT_SCHOOL = 'Dampol 1st National High School'


def remark_for(score):
    return 'Passed' if score >= PASSING_SCORE else 'Did not meet the passing grade'


def school_name():
    footer = SiteContent.objects.filter(document=SiteContent.Document.FOOTER).first()
    title = ((footer.payload or {}).get('schoolTitle') if footer else '') or ''
    return str(title).strip().title() or DEFAULT_SCHOOL


def _placement(profile, year):
    rows = StudentSection.objects.filter(student=profile, is_active=True).select_related(
        'section__program', 'school_year'
    )
    return (rows.filter(school_year=year).first() if year else None) or rows.first()


def allowed_subject_ids(user, profile, placement):
    """None = every subject. A set = only those subjects. Raises PermissionDenied when not allowed."""
    if user.role == User.Role.STUDENT:
        if profile.user_id != user.id:
            raise PermissionDenied('You can only print your own grades.')
        return None
    if user.role == User.Role.ADMIN:
        return None
    section = placement.section if placement else None
    if user.role == User.Role.HEAD_TEACHER:
        if section is None or not grade_in_scope(user, section.grade_level):
            raise PermissionDenied('That student is outside the grade levels you are assigned to.')
        return None
    if user.role == User.Role.TEACHER and section is not None:
        duties = TeacherAssignment.objects.filter(
            teacher=user,
            section=section,
            school_year=placement.school_year,
            status=TeacherAssignment.Status.ACTIVE,
        )
        if duties.filter(assignment_type=TeacherAssignment.Type.ADVISER).exists():
            return None
        subjects = set(
            duties.filter(assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER, subject__isnull=False).values_list(
                'subject_id', flat=True
            )
        )
        if subjects:
            return subjects
    raise PermissionDenied('You are not assigned to this student.')


class GradePrintView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'reports'  # heavy queries: repeated calls must not stall the server for everyone

    def get(self, request):
        user = request.user
        if user.role == User.Role.STUDENT:
            profile = get_object_or_404(StudentProfile.objects.select_related('user'), user=user)
        else:
            profile = get_object_or_404(StudentProfile.objects.select_related('user'), pk=request.query_params.get('student'))

        year = None
        if request.query_params.get('school_year'):
            year = get_object_or_404(SchoolYear, pk=request.query_params['school_year'])
        placement = _placement(profile, year)
        year = year or (placement.school_year if placement else SchoolYear.objects.filter(is_current=True).first())
        subject_ids = allowed_subject_ids(user, profile, placement)

        statuses = [Grade.Status.RELEASED]
        if user.role != User.Role.STUDENT:
            statuses.append(Grade.Status.APPROVED)
        grades = Grade.objects.filter(student=profile, status__in=statuses).select_related(
            'subject', 'term', 'school_year', 'teacher'
        )
        if year:
            grades = grades.filter(school_year=year)
        term = None
        if request.query_params.get('term'):
            term = get_object_or_404(Term, pk=request.query_params['term'], school_year=year)
            grades = grades.filter(term=term)
        if subject_ids is not None:
            grades = grades.filter(subject_id__in=subject_ids)
        grades = list(grades.order_by('term__number', 'subject__name'))

        section = placement.section if placement else None
        program = section.program if section and section.program_id else None
        teachers = {
            (row.section_id, row.subject_id): row.teacher.get_full_name() or row.teacher.email
            for row in TeacherAssignment.objects.filter(
                section=section,
                school_year=year,
                assignment_type=TeacherAssignment.Type.SUBJECT_TEACHER,
                status=TeacherAssignment.Status.ACTIVE,
            ).select_related('teacher')
        } if section else {}

        rows = [
            {
                'term': grade.term.label,
                'term_number': grade.term.number,
                'subject': grade.subject.name,
                'teacher': (grade.teacher.get_full_name() if grade.teacher_id else '')
                or teachers.get((grade.section_id or (section.id if section else None), grade.subject_id), ''),
                'grade': str(grade.score),
                'remarks': remark_for(grade.score),
            }
            for grade in grades
        ]
        overall = average([grade.score for grade in grades])
        year_terms = Term.objects.filter(school_year=year) if year else Term.objects.none()
        return Response(
            {
                'school': school_name(),
                'title': 'Report on Learner Grades',
                'generated_at': timezone.localtime(),
                'generated_by_role': user.role,
                'student': {
                    'name': profile.user.get_full_name(),
                    'lrn': profile.lrn,
                    'grade_level': (section.grade_level if section else '') or profile.grade_level,
                    'section': section_label(section) if section else '',
                    'program': program.code if program else '',
                    'program_name': program.name if program else '',
                },
                'school_year': year.label if year else '',
                'term': term.label if term else 'All terms',
                'terms': [{'id': row.id, 'label': row.label} for row in year_terms],
                'rows': rows,
                'overall_average': str(overall) if overall is not None else '',
                'passing_score': PASSING_SCORE,
            }
        )
