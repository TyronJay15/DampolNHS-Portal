import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

logger = logging.getLogger('apps.accounts.lifecycle')

from apps.accounts.codes import issue_code
from apps.accounts.mail import account_deactivated_email, activation_email
from apps.accounts.models import User
from apps.audit import services as audit
from apps.notifications.services import notify
from apps.people.models import Registration

ARCHIVE_REASON = 'Account archived by administrator.'
HIDDEN = (User.AccountStatus.ARCHIVED, User.AccountStatus.REMOVED, User.AccountStatus.SUSPENDED)


class AccountActionError(ValidationError):
    pass


def _reason(value):
    text = str(value or '').strip() or ARCHIVE_REASON
    return text[:500]


def _guard_last_admin(user):
    if (
        user.role == User.Role.ADMIN
        and not User.objects.filter(
            role=User.Role.ADMIN,
            account_status=User.AccountStatus.ACTIVE,
        ).exclude(pk=user.pk).exists()
    ):
        raise AccountActionError({'detail': 'The last administrator cannot be archived.'})


def archive_account(actor, user, reason=''):
    if actor.pk == user.pk:
        raise AccountActionError({'detail': 'You cannot archive your own account.'})
    if user.account_status in HIDDEN:
        raise AccountActionError({'detail': 'This account is already archived or removed.'})
    _guard_last_admin(user)

    note = _reason(reason)
    now = timezone.now()
    rejected_pending = False
    notify(
        [user],
        title='Account archived',
        body='Your school portal account was archived. Contact the school office if you need help.',
    )
    with transaction.atomic():
        user.account_status = User.AccountStatus.ARCHIVED
        user.approval_note = note[:255]
        user.approval_updated_at = now
        fields = ['account_status', 'approval_note', 'approval_updated_at']
        if user.role == User.Role.STUDENT:
            pending = (
                Registration.objects.select_for_update()
                .filter(user=user, status=Registration.Status.PENDING)
                .first()
            )
            if pending:
                user.approval_status = User.ApprovalStatus.REJECTED
                fields.append('approval_status')
                pending.status = Registration.Status.REJECTED
                pending.rejection_reason = note
                pending.reviewed_at = now
                pending.reviewed_by = actor
                pending.save(update_fields=['status', 'rejection_reason', 'reviewed_at', 'reviewed_by'])
                rejected_pending = True
        user.save(update_fields=fields)

    try:
        account_deactivated_email(user, note, rejected_pending=rejected_pending)
    except Exception:
        logger.exception('Archive email failed for %s', user.email)
    audit.record(
        user=actor,
        action='account_archived',
        summary=f'Archived {user.role} account {user.email}',
        target_type='User',
        target_id=user.id,
        details={'email': user.email, 'reason': note, 'rejected_pending': rejected_pending},
    )
    return {'rejected_pending': rejected_pending}


def deactivate_account(actor, user, reason=''):
    return archive_account(actor, user, reason)


def reactivate_account(actor, user):
    if user.account_status == User.AccountStatus.REMOVED:
        raise AccountActionError({'detail': 'A removed account cannot be restored.'})
    if user.account_status not in (
        User.AccountStatus.SUSPENDED,
        User.AccountStatus.ARCHIVED,
        User.AccountStatus.PENDING_ACTIVATION,
    ):
        raise AccountActionError({'detail': 'This account is not waiting for a new password.'})

    notify(
        [user],
        title='Account restored',
        body='Your account was restored. Set a new password with the activation code to sign in.',
        force=True,
    )
    code = issue_code(user, 'activate')
    activation_email(user, code)
    user.set_unusable_password()
    user.account_status = User.AccountStatus.PENDING_ACTIVATION
    user.approval_note = ''
    user.approval_updated_at = timezone.now()
    user.save(update_fields=['password', 'account_status', 'approval_note', 'approval_updated_at'])
    audit.record(
        user=actor,
        action='account_reactivated',
        summary=f'Restored {user.role} account {user.email}',
        target_type='User',
        target_id=user.id,
        details={'email': user.email},
    )
    return {'email': user.email}


def anonymize_account(actor, user):
    if actor.pk == user.pk:
        raise AccountActionError({'detail': 'You cannot remove your own account.'})
    if user.account_status == User.AccountStatus.REMOVED:
        raise AccountActionError({'detail': 'This account is already removed.'})
    if user.account_status not in (User.AccountStatus.ARCHIVED, User.AccountStatus.SUSPENDED):
        raise AccountActionError({'detail': 'Archive the account before deleting it.'})
    _guard_last_admin(user)

    old_email = user.email
    with transaction.atomic():
        user.email = f'removed+{user.id}@archived.invalid'
        user.username = user.email
        user.first_name = 'Removed'
        user.last_name = f'Account {user.id}'
        user.set_unusable_password()
        user.account_status = User.AccountStatus.REMOVED
        user.approval_note = 'Removed from archive.'
        user.approval_updated_at = timezone.now()
        user.save(
            update_fields=[
                'email',
                'username',
                'first_name',
                'last_name',
                'password',
                'account_status',
                'approval_note',
                'approval_updated_at',
            ]
        )
        profile = getattr(user, 'student_profile', None)
        if profile:
            profile.lrn = f'REMOVED-{user.id}'
            profile.middle_name = ''
            profile.contact_number = ''
            profile.address = ''
            profile.birthdate = None
            profile.gender = ''
            profile.guardian_name = ''
            profile.guardian_contact = ''
            profile.save(
                update_fields=[
                    'lrn',
                    'middle_name',
                    'contact_number',
                    'address',
                    'birthdate',
                    'gender',
                    'guardian_name',
                    'guardian_contact',
                    'updated_at',
                ]
            )
        teacher = getattr(user, 'teacher_profile', None)
        if teacher:
            teacher.employee_id = f'REMOVED-{user.id}'
            teacher.middle_name = ''
            teacher.contact_number = ''
            teacher.save(update_fields=['employee_id', 'middle_name', 'contact_number', 'updated_at'])

    audit.record(
        user=actor,
        action='account_removed',
        summary=f'Removed {user.role} account {old_email}',
        target_type='User',
        target_id=user.id,
        details={'email': old_email},
    )
    return {'id': user.id}
