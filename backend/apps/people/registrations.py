"""Approving and rejecting student registrations, shared by the Admin's screens and access requests.

The result email is queued in the same transaction as the decision (apps.accounts.outbox), so a
decision is never saved without its email, and a large batch does not wait for the mail server.
"""

from django.db import transaction
from django.utils import timezone

from apps.accounts import outbox
from apps.accounts.models import User
from apps.audit import services as audit
from apps.audit.catalog import ACCOUNTS
from apps.notifications.services import notify
from apps.people.models import Registration
from apps.people.serializers import RegistrationReviewSerializer


class AlreadyReviewed(Exception):
    """The registration is no longer pending."""


def _lock_pending(registration):
    """Lock the row and read it again inside the transaction, so two simultaneous decisions on the same
    registration cannot both find it pending: the second waits, then sees it reviewed."""
    locked = Registration.objects.select_for_update().select_related('user').get(pk=registration.pk)
    if locked.status != Registration.Status.PENDING:
        raise AlreadyReviewed
    return locked


def _payload(registration, email):
    registration.refresh_from_db()
    payload = dict(RegistrationReviewSerializer(registration).data)
    payload['email_status'] = outbox.state_of(email)
    return payload


def approve_registration(registration, actor):
    """Approve one pending registration: account, audit entry, notification, queued email.

    Used by the single and the bulk approval and by access requests, so all behave identically.
    Raises AlreadyReviewed when the registration is not pending. Returns the review payload plus
    the email's state: queued, waiting, sent or failed.
    """
    with transaction.atomic():
        registration = _lock_pending(registration)
        now = timezone.now()
        user = registration.user
        user.approval_status = User.ApprovalStatus.APPROVED
        user.account_status = User.AccountStatus.ACTIVE
        user.approval_note = ''
        user.approval_updated_at = now
        user.save(update_fields=['approval_status', 'account_status', 'approval_note', 'approval_updated_at'])
        registration.status = Registration.Status.APPROVED
        registration.rejection_reason = ''
        registration.reviewed_at = now
        registration.reviewed_by = actor
        registration.save(update_fields=['status', 'rejection_reason', 'reviewed_at', 'reviewed_by'])
        email = outbox.queue_registration_result(registration, approved=True)
    audit.record(
        user=actor,
        action='account_approved',
        summary=f'Approved student account {user.email}',
        target_type='User',
        target_id=user.id,
        details={'registration_id': registration.id, 'email': user.email},
    )
    notify(
        [user],
        title='Account approved',
        body='You can sign in now. The Head Teacher will place you in a section.',
        level='success',
        category=ACCOUNTS,
    )
    return _payload(registration, outbox.deliver_inline(email))


def reject_registration(registration, actor, reason):
    """Reject one pending registration with a reason: account, audit entry, queued email.

    Raises AlreadyReviewed when the registration is not pending. Returns the review payload plus
    the email's state.
    """
    with transaction.atomic():
        registration = _lock_pending(registration)
        now = timezone.now()
        user = registration.user
        user.approval_status = User.ApprovalStatus.REJECTED
        user.approval_note = reason[:255]
        user.approval_updated_at = now
        user.save(update_fields=['approval_status', 'approval_note', 'approval_updated_at'])
        registration.status = Registration.Status.REJECTED
        registration.rejection_reason = reason
        registration.reviewed_at = now
        registration.reviewed_by = actor
        registration.save(update_fields=['status', 'rejection_reason', 'reviewed_at', 'reviewed_by'])
        email = outbox.queue_registration_result(registration, approved=False, reason=reason)
    audit.record(
        user=actor,
        action='account_rejected',
        summary=f'Rejected student account {user.email}',
        target_type='User',
        target_id=user.id,
        details={'registration_id': registration.id, 'email': user.email, 'reason': reason},
    )
    return _payload(registration, outbox.deliver_inline(email))
