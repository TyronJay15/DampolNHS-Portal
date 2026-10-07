"""The values that change college recommendation results, and where they come from.

Every value lives in a versioned RecommenderConfig row; exactly one row is active and every saved
recommendation records which version it used. DEFAULTS is the first version, written by migration
ml.0007, and the documented origin of each value. A value is changed by an authorized admin saving a
new version, never by editing code.

    academic_tiers.strong / moderate
        Root-mean-square distance, in grade points, between a student's relative strengths and a
        program profile (apps.ml.features.distance). At or below "strong" is a Strong academic tier,
        at or below "moderate" is Moderate, above it Low. Expert-defined and provisional until the school
        panel approves them from the real distance distribution (manage.py recommender_readiness prints it).
    interest_tiers.high / medium
        Mean of the student's 1-5 scores for a family's interest types. 4.0 means "Like" on average,
        3.0 means "Unsure". Expert-defined, panel-approved.
    shortlist.primary / additional
        Product decision: three primary programs, then up to seven more.
    readiness.* / neighbors.*
        Kept so stored settings rows stay valid. They are not used by the live matcher.
"""

import logging
from copy import deepcopy

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.ml.models import RecommenderConfig

logger = logging.getLogger(__name__)

ACTIVE = 'active'

DEFAULTS = {
    'academic_tiers': {'strong': 3.0, 'moderate': 6.0},
    'interest_tiers': {'high': 4.0, 'medium': 3.0},
    'shortlist': {'primary': 3, 'additional': 7},
    'readiness': {
        'target_records': 150,
        'family_min': 10,
        'program_min': 10,
        'min_families': 3,
        'max_folds': 5,
        'min_folds': 3,
        'baseline_margin': 0.05,
        'max_fold_std': 0.10,
        'min_class_recall': 0.10,
    },
    'neighbors': {'min_pool': 100, 'min_group': 5},
}

# (group, key) -> (type, lowest, highest)
LIMITS = {
    ('academic_tiers', 'strong'): (float, 0.0, 50.0),
    ('academic_tiers', 'moderate'): (float, 0.0, 50.0),
    ('interest_tiers', 'high'): (float, 1.0, 5.0),
    ('interest_tiers', 'medium'): (float, 1.0, 5.0),
    ('shortlist', 'primary'): (int, 1, 5),
    ('shortlist', 'additional'): (int, 0, 10),
    ('readiness', 'target_records'): (int, 1, 100000),
    ('readiness', 'family_min'): (int, 3, 10000),
    ('readiness', 'program_min'): (int, 3, 10000),
    ('readiness', 'min_families'): (int, 2, 50),
    ('readiness', 'max_folds'): (int, 3, 10),
    ('readiness', 'min_folds'): (int, 2, 10),
    ('readiness', 'baseline_margin'): (float, 0.0, 1.0),
    ('readiness', 'max_fold_std'): (float, 0.0, 1.0),
    ('readiness', 'min_class_recall'): (float, 0.0, 1.0),
    ('neighbors', 'min_pool'): (int, 1, 100000),
    ('neighbors', 'min_group'): (int, 1, 1000),
}


class ConfigError(ValueError):
    """The submitted values are incomplete, out of range or inconsistent. The message says which."""


def validate_values(values):
    """Return a clean copy of a complete configuration, or raise ConfigError."""
    if not isinstance(values, dict):
        raise ConfigError('The configuration must be an object.')
    clean = {}
    for (group, key), (kind, low, high) in LIMITS.items():
        section = values.get(group)
        raw = section.get(key) if isinstance(section, dict) else None
        if raw is None:
            raise ConfigError(f'{group}.{key} is required.')
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConfigError(f'{group}.{key} must be a number.')
        if kind is int and not float(raw).is_integer():
            raise ConfigError(f'{group}.{key} must be a whole number.')
        number = kind(raw)
        if not low <= number <= high:
            raise ConfigError(f'{group}.{key} must be between {low} and {high}.')
        clean.setdefault(group, {})[key] = number
    if clean['academic_tiers']['strong'] > clean['academic_tiers']['moderate']:
        raise ConfigError('The strong academic cut-off cannot be above the moderate one.')
    if clean['interest_tiers']['medium'] > clean['interest_tiers']['high']:
        raise ConfigError('The medium interest cut-off cannot be above the high one.')
    if clean['readiness']['min_folds'] > clean['readiness']['max_folds']:
        raise ConfigError('The minimum number of folds cannot be above the maximum.')
    if clean['readiness']['family_min'] < clean['readiness']['min_folds']:
        raise ConfigError('A supported family needs at least as many records as the minimum number of folds.')
    if clean['readiness']['program_min'] < clean['readiness']['min_folds']:
        raise ConfigError('A supported program needs at least as many records as the minimum number of folds.')
    return clean


def active_config():
    """The active configuration row and its values. Falls back to DEFAULTS only if no row exists."""
    row = RecommenderConfig.objects.filter(active_marker=ACTIVE).first()
    if row is None:
        logger.warning('No active recommender configuration; using the documented defaults.')
        return None, deepcopy(DEFAULTS)
    return row, row.values


def create_version(values, *, user, note='', is_approved=False):
    """Save a new, inactive configuration version."""
    clean = validate_values(values)
    with transaction.atomic():
        latest = RecommenderConfig.objects.select_for_update().order_by('-version').first()
        return RecommenderConfig.objects.create(
            version=(latest.version + 1) if latest else 1,
            values=clean,
            note=note[:255],
            is_approved=is_approved,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )


def activate_version(config):
    """Make one version active. The unique marker guarantees a single active row even under races."""
    validate_values(config.values)
    try:
        with transaction.atomic():
            RecommenderConfig.objects.filter(active_marker=ACTIVE).exclude(pk=config.pk).update(active_marker=None)
            config.active_marker = ACTIVE
            config.activated_at = timezone.now()
            config.save(update_fields=['active_marker', 'activated_at'])
    except IntegrityError as exc:
        raise ConfigError('Another configuration was activated at the same moment. Try again.') from exc
    return config
