"""Compact recommendation payload for the staff grade screens (advisory roster, records, grade report).

A thin adapter over apps.ml.recommender.recommend(), the one ranking path, so these screens order and
label programs exactly as the student's College recommendation page does. Staff screens pass approved
and released grades; the student's own page uses released grades only.
"""

from apps.grading.models import Grade
from apps.ml.explain import LABELS, sentences
from apps.ml.features import transform
from apps.ml.knn_model import INSUFFICIENT, METHOD, STRONG, evidence_threshold
from apps.ml.recommender import StudentInput, evidence_for, recommend

ADVISORY = 'Advisory. A starting point for planning, not a decision and not an admission requirement.'
SUMMARY = {
    'too_few_skills': 'Not enough grades yet for a college recommendation.',
    'no_programs': 'No college programs are configured yet.',
    'no_evaluable': 'No college program can be evaluated from the grades so far.',
    'no_consent': 'The student has not agreed to the college recommendation yet.',
}


def recommendation_grades(student_ids, *, released_only):
    """Student id -> the grades a recommendation may read, across Grade 11 and 12.

    The one eligibility rule: a student's own view reads released grades only (nothing the adviser has not
    shown yet); staff views and training read approved and released grades. Drafts and submitted or
    returned grades never count.
    """
    statuses = [Grade.Status.RELEASED] if released_only else [Grade.Status.APPROVED, Grade.Status.RELEASED]
    by_student = {student_id: [] for student_id in student_ids}
    rows = Grade.objects.filter(student_id__in=list(by_student), status__in=statuses).select_related('subject')
    for grade in rows.order_by('student_id', 'school_year_id', 'term_id', 'subject_id'):
        by_student[grade.student_id].append(grade)
    return by_student


def _needs_text(labels):
    if not labels:
        return ''
    joined = labels[0] if len(labels) == 1 else ', '.join(labels[:-1]) + f' and {labels[-1]}'
    return f' Grades in {joined} would let more college programs be checked.'


def _course(match, recommendation, student, context):
    evidence = evidence_for(match, recommendation, student, context)
    comparison = match.comparison
    label = context.schema.label
    return {
        'code': match.candidate.code,
        'name': match.candidate.name,
        'family': match.candidate.family_name,
        'label': match.label,
        'label_text': LABELS[match.label],
        'tier': match.tier,
        'distance': round(comparison.distance, 2),
        'reason': ' '.join(sentences(evidence)[:1]),
        'strand_context': comparison.strand_context,
        'evidence': {
            'status': comparison.evidence,
            'observed': len(comparison.observed),
            'total': comparison.total,
            'coverage': round(100 * comparison.coverage, 2),
            'observed_domains': [label(key) for key in comparison.observed],
            'missing_domains': [label(key) for key in comparison.unobserved],
        },
    }


def gated_payload():
    """Staff screens show this when the student has not agreed to college recommendation."""
    return {
        'method': METHOD,
        'ready': False,
        'evidence': INSUFFICIENT,
        'overall': None,
        'skills': [],
        'courses': [],
        'summary': SUMMARY['no_consent'],
        'advisory': ADVISORY,
        'model': {'method': METHOD, 'feature_schema': '', 'catalog': '', 'trained_on_outcomes': False},
        'coverage': {
            'observed': 0,
            'dimensions': 0,
            'threshold': evidence_threshold(),
            'needs': [],
            'not_evaluated': 0,
            'excluded_subjects': [],
            'unmapped_subjects': [],
        },
    }


def recommend_payload(grades, context, *, program_code='', strand_group='', interest=None):
    features = transform(grades, context.schema, context.domains)
    schema = context.schema
    student = StudentInput(features=features, interest=interest, strand_group=strand_group, program_code=program_code)
    recommendation = recommend(student, context)
    payload = {
        'method': recommendation.method,
        'ready': recommendation.ready,
        'evidence': INSUFFICIENT,
        'overall': str(features.overall) if features.overall is not None else None,
        'skills': [
            {'key': key, 'label': schema.label(key), 'average': str(value)} for key, value in features.averages().items()
        ],
        'courses': [],
        'summary': SUMMARY.get(recommendation.reason, ''),
        'advisory': ADVISORY,
        'model': {
            'method': recommendation.method,
            'feature_schema': schema.version,
            'catalog': context.catalog,
            'trained_on_outcomes': recommendation.method != METHOD,
        },
        'coverage': {
            'observed': features.observed_count,
            'dimensions': len(schema.keys),
            'threshold': evidence_threshold(),
            'needs': [schema.label(key) for key, _count in recommendation.blocked.most_common()],
            'not_evaluated': recommendation.not_evaluated,
            'excluded_subjects': list(features.excluded),
            'unmapped_subjects': list(features.unmapped),
        },
    }
    if recommendation.reason == 'no_evaluable':
        payload['summary'] += _needs_text(payload['coverage']['needs'])
    if not recommendation.ready:
        return payload
    courses = [_course(match, recommendation, student, context) for match in recommendation.items]
    top = courses[0]
    payload.update({'evidence': top['evidence']['status'], 'courses': courses, 'summary': _summary(top)})
    return payload


def _summary(top):
    """The headline states how well supported the first program is, not just its name."""
    evidence = top['evidence']
    if evidence['status'] == STRONG:
        return f'First program to explore: {top["name"]} ({top["label_text"]}). {top["reason"]}'
    return (
        f'Closest so far: {top["name"]}, on limited evidence '
        f'({evidence["observed"]} of {evidence["total"]} of its skill areas have grades). {top["reason"]}'
    )

