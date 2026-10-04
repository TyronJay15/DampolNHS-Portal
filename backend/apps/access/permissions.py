"""Read access for tagged people on the owner's existing screens.

The owner role keeps its full permission. Someone holding a live tag for one of the listed
activities may only read (GET) what they need to prepare a proposal, limited to the tag's grade
levels. Every change still goes through an AccessRequest that the owner approves.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.access.activities import ACTIVITIES, tag_levels
from apps.access.services import live_tag
from apps.accounts.models import User
from apps.people.scope import head_grade_scope


def role_or_tagged(roles, *activity_keys, tagged_methods=SAFE_METHODS):
    """The roles' own permission, plus access for people tagged for one of the activities.

    Tagged people get read-only access unless tagged_methods says otherwise (e.g. uploading a photo
    for a proposal, which publishes nothing on its own).
    """
    roles = (roles,) if isinstance(roles, str) else tuple(roles)

    class RoleOrTagged(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if not (user and user.is_authenticated and user.can_sign_in):
                return False
            if user.role in roles:
                return True
            return request.method in tagged_methods and any(live_tag(user, key) for key in activity_keys)

    return RoleOrTagged


def reading_levels(user, *activity_keys):
    """Grade levels a screen may show this user, or None for every level.

    The owner sees their own scope (a head teacher's grade levels, an admin everything); a tagged
    person sees the levels of their tags; anyone else sees nothing.
    """
    owner_roles = {ACTIVITIES[key].owner_role for key in activity_keys}
    if user.role in owner_roles:
        return head_grade_scope(user) if user.role == User.Role.HEAD_TEACHER else None
    levels = set()
    for key in activity_keys:
        tag = live_tag(user, key)
        if tag is None:
            continue
        covered = tag_levels(tag)
        if covered is None:
            return None
        levels |= covered
    return levels


def filter_levels(rows, levels, field='grade_level'):
    return rows if levels is None else rows.filter(**{f'{field}__in': levels})
