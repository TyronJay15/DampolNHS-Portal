from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.can_sign_in
            and user.role == user.Role.ADMIN
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.can_sign_in
            and user.role == user.Role.TEACHER
        )


class IsHeadTeacher(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.can_sign_in
            and user.role == user.Role.HEAD_TEACHER
        )


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.can_sign_in
            and user.role == user.Role.STUDENT
        )


class IsStaffUser(BasePermission):
    """Teachers, head teacher, and administrators."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.can_sign_in
            and user.role in (user.Role.TEACHER, user.Role.HEAD_TEACHER, user.Role.ADMIN)
        )
