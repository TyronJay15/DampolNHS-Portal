from django.conf import settings
from django.db import models


def record(*, user, action, summary, target_type='', target_id='', details=None):
    from apps.audit.models import AuditLog

    return AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        actor_label=getattr(user, 'email', '') or '',
        actor_role=getattr(user, 'role', '') or '',
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id not in (None, '') else '',
        summary=summary,
        details=details or {},
    )
