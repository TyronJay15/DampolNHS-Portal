"""Saved recommendations for a student: build, reuse while nothing changed, and serialize.

A run is rebuilt only when its inputs change (released grades, the latest completed assessment, the
active configuration, the catalog or the feature schema). Serving is the k-NN matcher against
program profiles. The student-facing name is ML recommendation.
"""

import hashlib
import json

from django.db import transaction

from apps.grading.recommend import recommendation_grades
from apps.guidance.models import GuidanceConsent, RecommendationItem, RecommendationRun
from apps.guidance.selectors import active_consent, latest_completed, latest_run, shs_program
from apps.ml.explain import LABELS, TEMPLATE_VERSION, sentences
from apps.ml.features import transform
from apps.ml.knn_model import METHOD
from apps.ml.recommender import RecommenderContext, StudentInput, evidence_for, interest_profile, recommend
from apps.school.models import SkillDomain

METHOD_LABELS = {
    METHOD: 'ML recommendation',
    RecommendationRun.Method.HYBRID_ML: 'ML recommendation',
}
NOT_READY = {
    'too_few_skills': 'Recommendations appear once grades in at least three skill areas are shown on your card.',
    'no_programs': 'No college programs are open for recommendation yet.',
    'no_evaluable': 'None of the college programs can be checked against your shown grades yet.',
    'no_consent': 'Agree to college recommendation to see your matches.',
}
FALLBACK_NOTICE = 'Recommendations are temporarily being generated using the nearest-program matcher.'
FALLBACK_REASONS = {'model_error', 'model_unavailable', 'schema_changed'}


def _student_input(student, context):
    grades = recommendation_grades([student.pk], released_only=True)[student.pk]
    assessment = latest_completed(student)
    program = shs_program(student)
    features = transform(grades, context.schema, context.domains)
    student_input = StudentInput(
        features=features,
        interest=assessment.scores if assessment else None,
        strand_group=program.strand_group if program else '',
        program_code=program.code if program else '',
    )
    return student_input, assessment, grades


def _fingerprint(grades, assessment, student_input, context):
    parts = {
        'grades': sorted((grade.pk, str(grade.score), grade.subject_id) for grade in grades),
        'assessment': assessment.pk if assessment else None,
        'strand': [student_input.strand_group, student_input.program_code],
        'config': context.config_row.pk if context.config_row else None,
        'catalog': context.catalog,
        'schema': context.schema.version,
        'interest_map': sorted((family, sorted(types)) for family, types in context.family_types.items()),
        'templates': TEMPLATE_VERSION,
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def current_run(student):
    """The student's run for today's inputs: the saved one if nothing changed, otherwise a new one.

    Without assessment consent the matcher is not run and no row is saved.
    """
    if active_consent(student, GuidanceConsent.Kind.ASSESSMENT) is None:
        return None
    context = RecommenderContext()
    student_input, assessment, grades = _student_input(student, context)
    fingerprint = _fingerprint(grades, assessment, student_input, context)
    saved = latest_run(student)
    if saved and saved.fingerprint == fingerprint:
        return saved
    recommendation = recommend(student_input, context)
    features = student_input.features
    with transaction.atomic():
        run = RecommendationRun.objects.create(
            student=student,
            method=recommendation.method,
            family_model=None,
            program_model=None,
            assessment=assessment,
            instrument_version=assessment.instrument.version if assessment else None,
            config=context.config_row,
            feature_schema=context.schema.version,
            catalog_version=context.catalog,
            features={
                'skills': {key: str(value) for key, value in features.averages().items()},
                'overall': str(features.overall) if features.overall is not None else None,
                'strand_group': student_input.strand_group,
                'interest': student_input.interest,
                'needs': [context.schema.label(key) for key, _count in recommendation.blocked.most_common()],
            },
            fingerprint=fingerprint,
            ready=recommendation.ready,
            not_ready_reason=recommendation.reason,
            fallback_reason='',
        )
        items = []
        for rank, match in enumerate(recommendation.items, start=1):
            evidence = evidence_for(match, recommendation, student_input, context)
            evidence['explanation'] = {'sentences': sentences(evidence), 'template_version': TEMPLATE_VERSION}
            items.append(
                RecommendationItem(
                    run=run,
                    college_program_id=match.candidate.pk,
                    rank=rank,
                    tier=match.tier,
                    label=match.label,
                    evidence=evidence,
                )
            )
        RecommendationItem.objects.bulk_create(items)
    return latest_run(student)


def _item_payload(item):
    program = item.college_program
    explanation = item.evidence.get('explanation') or {}
    facts = {key: value for key, value in item.evidence.items() if key != 'explanation'}
    return {
        'rank': item.rank,
        'tier': item.tier,
        'label': item.label,
        'label_text': LABELS[item.label],
        'program': {
            'code': program.code,
            'name': program.name,
            'abbreviation': program.abbreviation,
            'family': program.family.name if program.family_id else '',
        },
        'evidence': facts,
        'explanation': explanation.get('sentences') or [],
    }


def _skills(values):
    labels = dict(SkillDomain.objects.filter(key__in=list(values)).values_list('key', 'label'))
    return [{'key': key, 'label': labels.get(key, key), 'value': value} for key, value in values.items()]


def empty_payload(reason='no_consent'):
    return {
        'id': None,
        'created_at': None,
        'ready': False,
        'not_ready': NOT_READY.get(reason, NOT_READY['no_consent']),
        'method': METHOD,
        'method_label': METHOD_LABELS[METHOD],
        'notice': '',
        'primary': [],
        'additional': [],
        'families': [],
        'skills': [],
        'needs': [],
        'strand_group': '',
        'interest': [],
        'versions': {
            'config': None,
            'config_approved': False,
            'instrument': None,
            'family_model': None,
            'program_model': None,
            'feature_schema': '',
            'catalog': '',
        },
    }


def run_payload(run):
    if run is None:
        return empty_payload()
    features = run.features or {}
    items = [_item_payload(item) for item in run.items.all()]
    families = []
    for item in items:
        if item['program']['family'] and item['program']['family'] not in families:
            families.append(item['program']['family'])
    return {
        'id': run.pk,
        'created_at': run.created_at,
        'ready': run.ready,
        'not_ready': NOT_READY.get(run.not_ready_reason, ''),
        'method': run.method,
        'method_label': METHOD_LABELS.get(run.method, METHOD_LABELS[METHOD]),
        'notice': FALLBACK_NOTICE if run.fallback_reason in FALLBACK_REASONS else '',
        'primary': [item for item in items if item['tier'] == RecommendationItem.Tier.PRIMARY],
        'additional': [item for item in items if item['tier'] == RecommendationItem.Tier.ADDITIONAL],
        'families': families,
        'skills': _skills(features.get('skills') or {}),
        'needs': features.get('needs') or [],
        'strand_group': features.get('strand_group') or '',
        'interest': interest_profile(features.get('interest')),
        'versions': {
            'config': run.config.version if run.config_id else None,
            'config_approved': bool(run.config and run.config.is_approved),
            'instrument': run.instrument_version,
            'family_model': _model_label(run.family_model),
            'program_model': _model_label(run.program_model),
            'feature_schema': run.feature_schema,
            'catalog': run.catalog_version,
        },
    }


def _model_label(run):
    return f'{run.algorithm} v{run.version}' if run else None


def program_fits(student, codes):
    """Code -> how the student's evidence relates to that program, for program pages and comparison.

    Uses the same recommend() call as the shortlist, so a program's label and wording always agree with it.
    """
    if active_consent(student, GuidanceConsent.Kind.ASSESSMENT) is None:
        return {code: {'status': 'unavailable', 'reason': NOT_READY['no_consent']} for code in codes}
    context = RecommenderContext()
    student_input, _assessment, _grades = _student_input(student, context)
    recommendation = recommend(student_input, context)
    ranked = {match.candidate.code: (position, match) for position, match in enumerate(recommendation.ranked, start=1)}
    comparisons = {row.candidate.code: row for row in recommendation.comparisons}
    fits = {}
    for code in codes:
        if code in ranked:
            position, match = ranked[code]
            evidence = evidence_for(match, recommendation, student_input, context)
            fits[code] = {
                'status': 'evaluated',
                'position': position,
                'label': match.label,
                'label_text': LABELS[match.label],
                'evidence': evidence,
                'explanation': sentences(evidence),
            }
        elif code in comparisons:
            fits[code] = {
                'status': 'not_checked',
                'unchecked': [context.schema.label(key) for key in comparisons[code].unobserved],
                'reason': NOT_READY.get(recommendation.reason, 'None of this program\'s skill areas have your grades yet.'),
            }
        else:
            fits[code] = {'status': 'unavailable'}
    return fits
