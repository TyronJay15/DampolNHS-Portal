"""The Admin's recommender screen: live-matcher totals and settings.

Totals only. Nothing here returns an individual student's answers or results.
"""

from copy import deepcopy

from django.db.models import Count
from rest_framework.exceptions import ValidationError

from apps.audit import services as audit
from apps.guidance.models import GuidanceConsent, InterestAssessment, RecommendationRun
from apps.guidance.selectors import active_instrument
from apps.ml.models import CollegeOutcome, RecommenderConfig
from apps.ml.recommender_config import (
    ConfigError,
    DEFAULTS,
    activate_version,
    active_config,
    create_version,
    validate_values,
)

RECENT = 10


def _config_payload(row):
    return {
        'id': row.pk,
        'version': row.version,
        'values': row.values,
        'note': row.note,
        'approved': row.is_approved,
        'active': row.active_marker is not None,
        'created_at': row.created_at,
        'activated_at': row.activated_at,
        'created_by': _person(row.created_by),
    }


def _person(user):
    return (user.get_full_name() or user.username) if user else ''


def _changes(before, after):
    """Each value that differs, as "group key: old → new", so the audit entry shows exactly what moved."""
    lines = []
    for group, values in after.items():
        for key, value in values.items():
            old = (before.get(group) or {}).get(key)
            if old != value:
                lines.append(f'{group.replace("_", " ")} {key.replace("_", " ")}: {old} → {value}')
    return '; '.join(lines)


def _usable_config(raw):
    """A complete configuration for the status screen. Incomplete stored rows fall back to defaults."""
    try:
        return validate_values(raw)
    except (ConfigError, TypeError):
        return deepcopy(DEFAULTS)


def status_payload():
    row, config = active_config()
    config = _usable_config(config)
    consents = dict(
        GuidanceConsent.objects.filter(withdrawn_at__isnull=True).values_list('kind').annotate(total=Count('id'))
    )
    outcomes = dict(CollegeOutcome.objects.values_list('status').annotate(total=Count('id')))
    instrument = active_instrument()
    return {
        'method': 'ml_recommendation',
        'totals': {
            'assessment_consents': consents.get(GuidanceConsent.Kind.ASSESSMENT, 0),
            'training_consents': consents.get(GuidanceConsent.Kind.TRAINING, 0),
            'completed_assessments': InterestAssessment.objects.filter(
                status=InterestAssessment.Status.COMPLETED
            ).values('student_id').distinct().count(),
            'students_with_recommendations': RecommendationRun.objects.values('student_id').distinct().count(),
            'outcomes_recorded': outcomes.get(CollegeOutcome.Status.RECORDED, 0),
            'outcomes_validated': outcomes.get(CollegeOutcome.Status.VALIDATED, 0),
        },
        'instrument': {'name': str(instrument), 'version': instrument.version} if instrument else None,
        'config': {**(_config_payload(row) if row else {'version': None, 'approved': False}), 'values': config},
    }


def config_versions():
    return {
        'defaults': DEFAULTS,
        'versions': [_config_payload(row) for row in RecommenderConfig.objects.select_related('created_by')[:RECENT]],
    }


def save_config(values, *, user, note, approved, activate):
    _, before = active_config()
    try:
        row = create_version(values, user=user, note=note, is_approved=approved)
        if activate:
            activate_version(row)
    except ConfigError as exc:
        raise ValidationError({'detail': str(exc)}) from exc
    audit.record(
        user=user,
        action='recommender_config_activated' if activate else 'recommender_config_saved',
        summary=f'Recommender settings v{row.version} {"saved and activated" if activate else "saved"}',
        target_type='RecommenderConfig',
        target_id=row.pk,
        details={'note': row.note, 'panel_approved': approved, 'changes': _changes(before, row.values) or 'No value changed'},
    )
    return row


def activate_config(row, *, user):
    try:
        activate_version(row)
    except ConfigError as exc:
        raise ValidationError({'detail': str(exc)}) from exc
    audit.record(
        user=user,
        action='recommender_config_activated',
        summary=f'Recommender settings v{row.version} activated',
        target_type='RecommenderConfig',
        target_id=row.pk,
    )
    return row
