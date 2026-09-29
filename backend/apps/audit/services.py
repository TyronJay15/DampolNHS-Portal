from apps.audit.catalog import family_for_action


def record(*, user, action, summary, target_type='', target_id='', details=None, family=''):
    from apps.audit.models import AuditLog

    return AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        actor_label=getattr(user, 'email', '') or '',
        actor_role=getattr(user, 'role', '') or '',
        action=action,
        family=family or family_for_action(action),
        target_type=target_type,
        target_id=str(target_id) if target_id not in (None, '') else '',
        summary=summary,
        details=details or {},
    )
