"""Academic scope of a head teacher, kept in the existing TeacherAssignment records.

A head teacher is assigned to grade levels with TeacherAssignment(assignment_type=head_teacher,
grade_level=...) for a school year (Django admin). Several head teachers can each hold different
grade levels. A head teacher with no such assignment keeps whole-school academic scope, so
existing single-head-teacher schools work unchanged. Admins and teachers are not affected.
"""

from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.people.models import TeacherAssignment

OUT_OF_SCOPE = 'This is outside the grade levels you are assigned to.'


def head_grade_scope(user):
    """Grade levels a head teacher may manage this year, or None for the whole school."""
    if getattr(user, 'role', None) != User.Role.HEAD_TEACHER:
        return None
    levels = set(
        TeacherAssignment.objects.filter(
            teacher=user,
            assignment_type=TeacherAssignment.Type.HEAD_TEACHER,
            status=TeacherAssignment.Status.ACTIVE,
            school_year__is_current=True,
        )
        .exclude(grade_level='')
        .values_list('grade_level', flat=True)
    )
    return levels or None


def grade_in_scope(user, grade_level):
    scope = head_grade_scope(user)
    return scope is None or not grade_level or grade_level in scope


def require_grade_in_scope(user, grade_level):
    if not grade_in_scope(user, grade_level):
        raise PermissionDenied(OUT_OF_SCOPE)


def scope_by_grade(user, queryset, field='grade_level'):
    """Limit a queryset to the head teacher's grade levels (unchanged for everyone else)."""
    scope = head_grade_scope(user)
    return queryset if scope is None else queryset.filter(**{f'{field}__in': scope})
