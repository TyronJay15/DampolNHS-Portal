"""Activation figures per staff member, for the Admin's staff list.

Codes sent come from the mail log (apps.accounts.models.MailOutbox, kind activation), which records
every activation email with its result. Activations come from used activation codes. A count starts
when logging began, so staff created earlier show no sends until a new code goes out.
"""

from django.utils import timezone

from apps.accounts.models import EmailCode, MailOutbox, User

ACTIVATING_ROLES = (User.Role.TEACHER, User.Role.HEAD_TEACHER)


def _empty():
    return {
        'codes_sent': 0,
        'attempts': 0,
        'last_attempt_at': None,
        'last_result': None,
        'last_error': '',
        'activated_times': 0,
        'activated_at': None,
        'waiting_days': None,
    }


def activation_figures(users):
    """{user id: figures} for the teachers and Head Teacher among `users`. Others are left out."""
    staff = [user for user in users if user.role in ACTIVATING_ROLES]
    figures = {user.id: _empty() for user in staff}
    if not staff:
        return figures

    rows = MailOutbox.objects.filter(kind=MailOutbox.Kind.ACTIVATION, user_id__in=figures).order_by('id')
    for row in rows:
        item = figures[row.user_id]
        item['attempts'] += 1
        item['codes_sent'] += row.status == MailOutbox.Status.SENT
        item['last_attempt_at'] = row.sent_at or row.created_at
        item['last_result'] = row.status
        item['last_error'] = row.last_error

    issued = {}
    codes = EmailCode.objects.filter(purpose=EmailCode.Purpose.ACTIVATE, user_id__in=figures).order_by('created_at')
    for code in codes:
        item = figures[code.user_id]
        issued[code.user_id] = code.created_at
        if code.used_at:
            item['activated_times'] += 1
            item['activated_at'] = max(filter(None, (item['activated_at'], code.used_at)))

    now = timezone.now()
    for user in staff:
        if user.account_status == User.AccountStatus.PENDING_ACTIVATION:
            since = issued.get(user.id) or user.date_joined
            figures[user.id]['waiting_days'] = max(0, (now - since).days)
    return figures
