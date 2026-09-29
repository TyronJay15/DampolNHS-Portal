from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.people.models import TeacherAssignment


def notify(users, title, body, force=False, level='info', action_path='', category=''):
    seen = set()
    rows = []
    for user in users:
        if user is None or user.id in seen:
            continue
        if not force:
            if getattr(user, 'account_status', None) != User.AccountStatus.ACTIVE:
                continue
            if getattr(user, 'approval_status', None) != User.ApprovalStatus.APPROVED:
                continue
        seen.add(user.id)
        from apps.audit.catalog import infer_notification_category

        rows.append(
            Notification(
                user=user,
                title=title,
                body=body,
                category=category or infer_notification_category(title, body),
                level=level,
                action_path=action_path or '',
            )
        )
    if not rows:
        return 0
    Notification.objects.bulk_create(rows)
    return len(rows)


def active_users(*roles):
    qs = User.objects.filter(
        account_status=User.AccountStatus.ACTIVE,
        approval_status=User.ApprovalStatus.APPROVED,
    )
    if roles:
        qs = qs.filter(role__in=roles)
    return list(qs)


def teachers_for_year(school_year):
    ids = TeacherAssignment.objects.filter(
        school_year=school_year,
        status=TeacherAssignment.Status.ACTIVE,
    ).values_list('teacher_id', flat=True)
    return list(
        User.objects.filter(
            id__in=ids,
            account_status=User.AccountStatus.ACTIVE,
            approval_status=User.ApprovalStatus.APPROVED,
        )
    )


def head_teachers():
    return active_users(User.Role.HEAD_TEACHER)


def advisers_for_section(section):
    ids = TeacherAssignment.objects.filter(
        section=section,
        school_year=section.school_year,
        assignment_type=TeacherAssignment.Type.ADVISER,
        status=TeacherAssignment.Status.ACTIVE,
    ).values_list('teacher_id', flat=True)
    return list(
        User.objects.filter(
            id__in=ids,
            account_status=User.AccountStatus.ACTIVE,
            approval_status=User.ApprovalStatus.APPROVED,
        )
    )
