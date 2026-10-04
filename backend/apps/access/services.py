"""Granting and closing tags, and the life of a request: submit, withdraw, approve, decline, expire.

Every step is written to the audit log (family "access") and the other side is notified.
The server enforces the rules, not the screens: only the owner role tags and decides, nobody decides
their own request, a head teacher stays inside their grade levels, and students are never involved.
"""

from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.access.activities import ACTIVITIES, EXECUTION_ERRORS, ActivityFailed, my_access_path, tag_levels
from apps.access.models import AccessRequest, AccessTag
from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import User
from apps.audit import services as audit
from apps.audit.catalog import ACCESS
from apps.notifications.services import notify
from apps.people.scope import head_grade_scope

REQUEST_DAYS = 14


def _activity(key):
    activity = ACTIVITIES.get(key)
    if activity is None:
        raise ValidationError({'detail': 'Unknown activity.'})
    return activity


def _name(user):
    return (user.get_full_name() or user.email) if user else 'Someone'


def _owner_path(activity):
    return '/admin/access' if activity.owner_role == User.Role.ADMIN else '/head/access'


def live_tags(user, activity_key=None):
    rows = AccessTag.objects.filter(holder=user, status=AccessTag.Status.ACTIVE).filter(
        Q(ends_on__isnull=True) | Q(ends_on__gte=timezone.localdate())
    )
    if activity_key:
        rows = rows.filter(activity=activity_key)
    return rows.select_related('granted_by')


def live_tag(user, activity_key):
    return live_tags(user, activity_key).first()


def owns(user, activity):
    return bool(user and user.is_authenticated and user.can_sign_in and user.role == activity.owner_role)


def covers(owner, tag):
    """True when this owner may manage the tag: any admin for admin activities; a head teacher within scope."""
    if not owns(owner, _activity(tag.activity)):
        return False
    if owner.role == User.Role.ADMIN or tag.granted_by_id == owner.id:
        return True
    scope = head_grade_scope(owner)
    if scope is None:
        return True
    levels = tag_levels(tag)
    return levels is not None and levels <= set(scope)


def holders_for(owner, activity):
    """People this owner may tag for the activity: active staff of the holder roles, never a student."""
    if not owns(owner, activity):
        return User.objects.none()
    return (
        User.objects.filter(role__in=activity.holder_roles, is_active=True)
        .exclude(account_status__in=HIDDEN)
        .exclude(pk=owner.pk)
        .order_by('last_name', 'first_name')
    )


def grant(owner, *, holder_id, activity_key, scope='', ends_on=None, no_end_date=False, note=''):
    activity = _activity(activity_key)
    if not owns(owner, activity):
        raise PermissionDenied('Only the owner of this activity can tag someone for it.')
    holder = holders_for(owner, activity).filter(pk=holder_id).first()
    if holder is None:
        raise ValidationError({'detail': 'Choose an active person who can be tagged for this activity.'})
    scope = str(scope or '').strip()
    if scope and scope not in {option['value'] for option in activity.scope_options(owner)}:
        raise ValidationError({'detail': f'Choose from the {activity.scope_label.lower()} you manage.'})
    if not no_end_date:
        if not ends_on:
            raise ValidationError({'detail': 'Set an end date, or choose "No end date".'})
        try:
            ends_on = ends_on if isinstance(ends_on, date) else date.fromisoformat(str(ends_on))
        except ValueError as exc:
            raise ValidationError({'detail': 'Enter a valid end date.'}) from exc
        if ends_on < timezone.localdate():
            raise ValidationError({'detail': 'The end date cannot be in the past.'})
    else:
        ends_on = None
    if live_tag(holder, activity.key):
        raise ValidationError({'detail': f'{_name(holder)} already has this tag. Close it before tagging again.'})
    tag = AccessTag.objects.create(
        activity=activity.key,
        holder=holder,
        granted_by=owner,
        scope=scope,
        ends_on=ends_on,
        note=str(note or '').strip()[:255],
    )
    until = f'until {ends_on:%b %d, %Y}' if ends_on else 'with no end date'
    audit.record(
        user=owner,
        action='access_tag_granted',
        summary=f'Tagged {_name(holder)} for {activity.label} ({scope or "no limit"}, {until})',
        target_type='AccessTag',
        target_id=tag.id,
        details={'holder': holder.id, 'activity': activity.key, 'scope': scope, 'ends_on': str(ends_on or '')},
    )
    notify(
        [holder],
        title=f'Access granted · {activity.label}',
        body=f'{_name(owner)} tagged you to prepare "{activity.label}" {until}. The owner approves each request.',
        category=ACCESS,
        action_path=my_access_path(holder),
    )
    return tag


def close_tag(owner, tag, reason):
    reason = str(reason or '').strip()
    if not reason:
        raise ValidationError({'detail': 'Give a reason for closing this tag.'})
    if not covers(owner, tag):
        raise PermissionDenied('You cannot close this tag.')
    if tag.status == AccessTag.Status.CLOSED:
        raise ValidationError({'detail': 'This tag is already closed.'})
    activity = _activity(tag.activity)
    now = timezone.now()
    tag.status = AccessTag.Status.CLOSED
    tag.closed_at = now
    tag.closed_by = owner
    tag.close_reason = reason[:255]
    tag.save(update_fields=['status', 'closed_at', 'closed_by', 'close_reason'])
    cancelled = 0
    for request in tag.requests.filter(status=AccessRequest.Status.PENDING):
        request.status = AccessRequest.Status.WITHDRAWN
        request.decided_at = now
        request.decision_note = 'Cancelled because the tag was closed.'
        request.save(update_fields=['status', 'decided_at', 'decision_note'])
        activity.discard(request.payload)
        cancelled += 1
    audit.record(
        user=owner,
        action='access_tag_closed',
        summary=f'Closed the {activity.label} tag of {_name(tag.holder)}',
        target_type='AccessTag',
        target_id=tag.id,
        details={'reason': reason, 'cancelled_requests': cancelled},
    )
    notify(
        [tag.holder],
        title=f'Access closed · {activity.label}',
        body=f'{_name(owner)} closed your "{activity.label}" tag. Reason: {reason}',
        level='warning',
        category=ACCESS,
        action_path=my_access_path(tag.holder),
    )
    return tag


def _owners_to_notify(tag, activity):
    if tag.granted_by is not None and tag.granted_by.can_sign_in:
        return [tag.granted_by]
    return list(User.objects.filter(role=activity.owner_role, is_active=True).exclude(account_status__in=HIDDEN))


def submit(proposer, activity_key, payload, note):
    activity = _activity(activity_key)
    tag = live_tag(proposer, activity.key)
    if tag is None:
        raise PermissionDenied('You do not have an active tag for this activity.')
    note = str(note or '').strip()
    if not note:
        raise ValidationError({'detail': 'Add a note so the owner knows why.'})
    if not isinstance(payload, dict):
        raise ValidationError({'detail': 'Nothing to submit.'})
    # The 'before' snapshot is the server's to take; never trust one sent by the browser.
    payload = {key: value for key, value in payload.items() if key != 'before'}
    cleaned = activity.clean(payload, tag, proposer)
    request = AccessRequest.objects.create(
        tag=tag,
        activity=activity.key,
        requested_by=proposer,
        payload=cleaned,
        summary=activity.describe(cleaned),
        changes=activity.diff(cleaned),
        note=note[:1000],
        expires_at=timezone.now() + timedelta(days=REQUEST_DAYS),
    )
    audit.record(
        user=proposer,
        action='access_request_submitted',
        summary=f'Submitted for approval: {request.summary}',
        target_type='AccessRequest',
        target_id=request.id,
        details={'activity': activity.key, 'payload': cleaned, 'note': request.note},
    )
    notify(
        _owners_to_notify(tag, activity),
        title=f'Approval needed · {activity.label}',
        body=f'{_name(proposer)}: {request.summary}',
        category=ACCESS,
        action_path=_owner_path(activity),
    )
    return request


def withdraw(proposer, request):
    if request.requested_by_id != proposer.id:
        raise PermissionDenied('Only the person who submitted this request can withdraw it.')
    if request.status != AccessRequest.Status.PENDING:
        raise ValidationError({'detail': 'This request is no longer waiting.'})
    request.status = AccessRequest.Status.WITHDRAWN
    request.decided_at = timezone.now()
    request.save(update_fields=['status', 'decided_at'])
    _activity(request.activity).discard(request.payload)
    audit.record(
        user=proposer,
        action='access_request_withdrawn',
        summary=f'Withdrew: {request.summary}',
        target_type='AccessRequest',
        target_id=request.id,
    )
    return request


def can_decide(user, request):
    return user.id != request.requested_by_id and covers(user, request.tag)


def _finish(request, owner, status, note='', result=None):
    request.status = status
    request.decided_by = owner
    request.decided_at = timezone.now()
    request.decision_note = str(note or '')[:255]
    request.result = result or {}
    request.save(update_fields=['status', 'decided_by', 'decided_at', 'decision_note', 'result'])


def decide(owner, request, approve, note=''):
    expire_due()
    request.refresh_from_db()
    if request.status != AccessRequest.Status.PENDING:
        raise ValidationError({'detail': 'This request is no longer waiting.'})
    if not can_decide(owner, request):
        raise PermissionDenied('You cannot decide this request.')
    activity = _activity(request.activity)
    note = str(note or '').strip()
    proposer = request.requested_by
    if not approve:
        if not note:
            raise ValidationError({'detail': 'Give a reason for declining.'})
        _finish(request, owner, AccessRequest.Status.DECLINED, note)
        activity.discard(request.payload)
        audit.record(
            user=owner,
            action='access_request_declined',
            summary=f'Declined: {request.summary}',
            target_type='AccessRequest',
            target_id=request.id,
            details={'proposed_by': _name(proposer), 'reason': note},
        )
        notify(
            [proposer],
            title=f'Request declined · {activity.label}',
            body=f'{_name(owner)} declined "{request.summary}". Reason: {note}',
            level='warning',
            category=ACCESS,
            action_path=my_access_path(proposer),
        )
        return request
    # Checked again now: the data may have changed since the request was prepared.
    try:
        cleaned = activity.clean(request.payload, request.tag, proposer)
        result = activity.execute(cleaned, owner)
    except (ActivityFailed, *EXECUTION_ERRORS) as exc:
        reason = _error_text(exc)
        _finish(request, owner, AccessRequest.Status.FAILED, note, {'error': reason})
        activity.discard(request.payload)
        audit.record(
            user=owner,
            action='access_request_failed',
            summary=f'Could not apply: {request.summary}',
            target_type='AccessRequest',
            target_id=request.id,
            details={'proposed_by': _name(proposer), 'error': reason},
        )
        notify(
            [proposer],
            title=f'Request could not be applied · {activity.label}',
            body=f'"{request.summary}" was approved but could not be applied: {reason}',
            level='warning',
            category=ACCESS,
            action_path=my_access_path(proposer),
        )
        return request
    _finish(request, owner, AccessRequest.Status.APPROVED, note, result)
    audit.record(
        user=owner,
        action='access_request_approved',
        summary=f'Approved and applied: {request.summary} (proposed by {_name(proposer)})',
        target_type='AccessRequest',
        target_id=request.id,
        details={'proposed_by': _name(proposer), 'note': note, 'result': result},
    )
    notify(
        [proposer],
        title=f'Request approved · {activity.label}',
        body=f'{_name(owner)} approved and applied "{request.summary}".',
        level='success',
        category=ACCESS,
        action_path=my_access_path(proposer),
    )
    return request


def _error_text(exc):
    detail = getattr(exc, 'detail', None)
    if isinstance(detail, dict):
        detail = detail.get('detail') or next(iter(detail.values()), '')
    if isinstance(detail, list):
        detail = ' '.join(str(item) for item in detail)
    return str(detail or exc or 'Something changed since this was prepared.')


def expire_due():
    """Requests nobody decided within REQUEST_DAYS stop waiting. Runs whenever requests are listed or decided."""
    for request in AccessRequest.objects.filter(
        status=AccessRequest.Status.PENDING, expires_at__lt=timezone.now()
    ).select_related('requested_by'):
        request.status = AccessRequest.Status.EXPIRED
        request.decided_at = timezone.now()
        request.save(update_fields=['status', 'decided_at'])
        if request.activity in ACTIVITIES:
            ACTIVITIES[request.activity].discard(request.payload)
        audit.record(
            user=None,
            action='access_request_expired',
            summary=f'Expired without a decision: {request.summary}',
            target_type='AccessRequest',
            target_id=request.id,
        )
        notify(
            [request.requested_by],
            title='Request expired',
            body=f'"{request.summary}" was not decided within {REQUEST_DAYS} days. Submit it again if it is still needed.',
            level='warning',
            category=ACCESS,
            action_path=my_access_path(request.requested_by),
        )
