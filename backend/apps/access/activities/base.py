"""Shared pieces of every activity: the base class, scope checks and the before/after helpers."""

import re

from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.people.scope import head_grade_scope
from apps.school.curriculum import GRADE_LEVELS

ADMIN = User.Role.ADMIN
HEAD_TEACHER = User.Role.HEAD_TEACHER
TEACHER = User.Role.TEACHER

# Errors an approved request can hit when it is finally carried out (the data may have changed).
EXECUTION_ERRORS = (ValidationError, PermissionDenied, Http404, ValueError)

# The dashboard area of each role that can be tagged.
AREA = {HEAD_TEACHER: 'head', TEACHER: 'teacher'}


def my_access_path(user):
    return f'/{AREA.get(user.role, "teacher")}/my-access'


class ActivityFailed(Exception):
    """The approved request could not be carried out; the message says why."""


def tag_levels(tag):
    """Grade levels a tag covers, or None for every level."""
    if tag.scope:
        return {tag.scope}
    granter = tag.granted_by
    if granter is not None and granter.role == HEAD_TEACHER:
        scope = head_grade_scope(granter)
        return set(scope) if scope is not None else None
    return None


def require_level(tag, grade_level, what):
    levels = tag_levels(tag)
    if levels is not None and grade_level not in levels:
        raise ValidationError({'detail': f'{what} is outside the grade levels this tag covers.'})


def ids_from(value, label, limit):
    if not isinstance(value, list) or not value:
        raise ValidationError({'detail': f'Choose at least one {label}.'})
    if len(value) > limit:
        raise ValidationError({'detail': f'Send at most {limit} {label}s in one request.'})
    try:
        return sorted({int(item) for item in value})
    except (TypeError, ValueError) as exc:
        raise ValidationError({'detail': f'Each {label} must be an id.'}) from exc


def names_text(names, limit=3):
    shown = ', '.join(names[:limit])
    return f'{shown} +{len(names) - limit} more' if len(names) > limit else shown


def short(text):
    return text if len(text) <= 255 else f'{text[:252]}...'


def humanize(key):
    """'heroTitle' or 'hero_title' -> 'Hero title'."""
    words = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(key)).replace('_', ' ').strip().lower()
    return words[:1].upper() + words[1:]


def _plain(value):
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if value in (None, ''):
        return None
    if isinstance(value, (list, tuple)):
        return ', '.join(str(item) for item in value) or None
    return str(value)


def change(label, before, after):
    """One row of a request's before/after view."""
    return {'label': label, 'before': _plain(before), 'after': _plain(after)}


def _leaves(value, path):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, (*path, humanize(key)))
    elif isinstance(value, list) and value and all(isinstance(item, (dict, list)) for item in value):
        for index, item in enumerate(value, start=1):
            yield from _leaves(item, (*path, str(index)))
    else:
        yield ' · '.join(path), value


def field_changes(before, after):
    """Before/after rows for nested content (e.g. a CMS page), only where a value really changed."""
    rows = []
    for key in after:
        old = dict(_leaves(before.get(key), (humanize(key),)))
        new = dict(_leaves(after[key], (humanize(key),)))
        for path in [*new, *(path for path in old if path not in new)]:
            if old.get(path) != new.get(path):
                rows.append(change(path, old.get(path), new.get(path)))
    return rows


class Activity:
    key = ''
    label = ''
    description = ''
    owner_role = ''
    holder_roles = ()
    work_slug = ''
    scope_label = 'Grade levels'
    scope_all = 'All levels'

    def clean(self, payload, tag, proposer):
        """The proposal as it will be stored and approved. Raises ValidationError when it does not fit.

        Activities that guard against later edits keep a 'before' snapshot in the cleaned payload; it is
        taken on submit (any 'before' sent by the browser is dropped) and kept when re-checked on approval.
        """
        raise NotImplementedError

    def describe(self, cleaned):
        raise NotImplementedError

    def diff(self, cleaned):
        """Before/after rows for the owner, taken when the request is submitted."""
        return []

    def execute(self, cleaned, owner):
        """Carry out the approved proposal as the owner. Raises ActivityFailed when it cannot be done."""
        raise NotImplementedError

    def discard(self, payload):
        """Tidy up after a request that will never be applied (declined, withdrawn, expired, failed)."""

    def scope_options(self, owner):
        """What a tag for this activity can be limited to; an empty list means it has no scope."""
        scope = head_grade_scope(owner) if owner.role == HEAD_TEACHER else None
        levels = list(scope) if scope is not None else list(GRADE_LEVELS)
        return [{'value': level, 'label': level} for level in levels]

    def scope_text(self, scope):
        """How a tag's scope reads on screen."""
        return scope or self.scope_all

    def work_path(self, role):
        """Where a tagged person of this role prepares the work (the owner's page in proposal mode)."""
        return f'/{AREA[role]}/access/{self.work_slug}'

    def as_dict(self, owner):
        return {
            'key': self.key,
            'label': self.label,
            'description': self.description,
            'owner_role': self.owner_role,
            'holder_roles': list(self.holder_roles),
            'scope_label': self.scope_label,
            'scope_all': self.scope_all,
            'scope_options': self.scope_options(owner),
        }
