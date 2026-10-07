"""Every guidance authorization rule, in one place. Views call these; no view invents its own check.

Students never pass a student id: their endpoints read the signed-in user's own profile. Advisers reach a
student only through their own active adviser assignment, checked for that exact student. A failed object
check answers 404, the same as a missing record, so ids cannot be probed.
"""

from django.http import Http404
from rest_framework.permissions import BasePermission

from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile, User
from apps.people.models import StudentSection, TeacherAssignment


def _signed_in(user):
    return bool(user and user.is_authenticated and user.can_sign_in)


class IsGuidanceStudent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return _signed_in(user) and user.role == User.Role.STUDENT and hasattr(user, 'student_profile')


class IsGuidanceAdviser(BasePermission):
    def has_permission(self, request, view):
        return _signed_in(request.user) and request.user.role == User.Role.TEACHER


class IsGuidanceAdmin(BasePermission):
    def has_permission(self, request, view):
        return _signed_in(request.user) and request.user.role == User.Role.ADMIN


class CanReadCatalog(BasePermission):
    """The active program catalog is readable by every signed-in portal user."""

    def has_permission(self, request, view):
        return _signed_in(request.user)


def adviser_assignment(user, assignment_id):
    """The user's own active adviser assignment, or 404."""
    assignment = (
        TeacherAssignment.objects.filter(
            pk=assignment_id,
            teacher=user,
            assignment_type=TeacherAssignment.Type.ADVISER,
            status=TeacherAssignment.Status.ACTIVE,
            section__isnull=False,
        )
        .select_related('section', 'section__program', 'school_year')
        .first()
    )
    if assignment is None:
        raise Http404
    return assignment


def advisee(assignment, student_id):
    """A student actively placed in the assignment's section and year, or 404."""
    placed = StudentSection.objects.filter(
        section=assignment.section,
        school_year=assignment.school_year,
        is_active=True,
        student_id=student_id,
    ).exclude(student__user__account_status__in=HIDDEN).exists()
    if not placed:
        raise Http404
    return StudentProfile.objects.select_related('user').get(pk=student_id)
