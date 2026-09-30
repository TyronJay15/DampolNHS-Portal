from apps.ml.features import load_schema, transform
from apps.ml.knn_model import (
    INSUFFICIENT,
    METHOD,
    STRONG,
    catalog_version,
    evidence_threshold,
    load_candidates,
    rank,
)

MIN_SKILLS = 3
ADVISORY = 'Advisory. Based on subjects shown so far. Not an admission decision.'


class RecommendationContext:
    """Schema, college profiles and subject domains loaded once and shared across a request."""

    def __init__(self):
        self.schema = load_schema()
        self.candidates = load_candidates(self.schema)
        self.catalog = catalog_version(self.candidates)
        self.domains = {}


def _needs_text(labels):
    if not labels:
        return ''
    joined = labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + f' and {labels[-1]}'
    return f' Grades in {joined} would let more college programs be checked.'


def recommend_payload(grades, program_code=None, context=None):
    context = context or RecommendationContext()
    features = transform(grades, context.schema, context.domains)
    schema = context.schema
    skills = [
        {'key': key, 'label': schema.label(key), 'average': str(value)}
        for key, value in features.averages().items()
    ]
    payload = {
        'method': METHOD,
        'ready': False,
        'evidence': INSUFFICIENT,
        'overall': str(features.overall) if features.overall is not None else None,
        'skills': skills,
        'courses': [],
        'summary': '',
        'advisory': ADVISORY,
        'model': {
            'method': METHOD,
            'feature_schema': schema.version,
            'catalog': context.catalog,
            'trained_on_outcomes': False,
        },
        'coverage': {
            'observed': features.observed_count,
            'dimensions': len(schema.keys),
            'threshold': evidence_threshold(),
            'needs': [],
            'not_evaluated': 0,
            'excluded_subjects': list(features.excluded),
            'unmapped_subjects': list(features.unmapped),
        },
    }
    if features.observed_count < MIN_SKILLS:
        payload['summary'] = 'Not enough shown grades yet for a college recommendation.'
        return payload
    if not context.candidates:
        payload['summary'] = 'No college programs are configured yet.'
        return payload

    ranking = rank(features, context.candidates, program_code)
    courses = ranking.courses
    needs = [schema.label(key) for key, _count in ranking.blocked.most_common()]
    payload['coverage'].update({'needs': needs, 'not_evaluated': ranking.not_evaluated})
    if not courses:
        payload['summary'] = 'No college course can be evaluated from the grades shown so far.' + _needs_text(needs)
        return payload
    top = courses[0]
    payload.update(
        {
            'ready': True,
            'evidence': top['evidence']['status'],
            'courses': courses,
            'summary': _summary(top),
        }
    )
    return payload


def _summary(top):
    """The headline states how well supported the closest program is, not just its name."""
    evidence = top['evidence']
    if evidence['status'] == STRONG:
        return f'Top match: {top["name"]}. {top["reason"]}'
    return (
        f'Closest so far: {top["name"]}, on limited evidence '
        f'({evidence["observed"]} of {evidence["total"]} of its skill areas have grades). {top["reason"]}'
    )
