"""The single recommendation path. Every screen, the adviser view, the API and saved runs call recommend().

Live serving is one k-NN nearest-program matcher against validated program profiles, using this student's
grades, SHS interest answers and strand. Strand is a last tie-break, not a gate.

Steps:
1. Profile matching compares the student with every active program (knn_model.compare_all).
2. Programs whose benchmark areas all have grades come first; an unchecked benchmark follows them and is
   labeled Limited Evidence, but is never removed. Below-benchmark counts then move rank (a floor is
   guidance, not a gate). Within that: academic tier, interest tier, distance, then strand as a
   tie-break (typical pathway before other), then name. There is no weighted blend.
3. Labels depend only on the student's own evidence and the active configuration.
4. The shortlist is the first `primary` programs, then up to `additional` more that reach at least a
   Moderate academic tier.
"""

from collections import Counter
from dataclasses import dataclass, field

from apps.ml.features import RIASEC_ORDER, load_schema
from apps.ml.knn_model import BELOW, INSUFFICIENT, LIMITED, METHOD, TYPICAL, compare_all, catalog_version, load_candidates
from apps.ml.models import FamilyInterestMap, RiasecType
from apps.ml.recommender_config import active_config

MIN_SKILLS = 3

STRONG = 'strong'
MODERATE = 'moderate'
LOW = 'low'
HIGH = 'high'
MEDIUM = 'medium'
NOT_ASSESSED = 'not_assessed'

GOOD = 'good'
POSSIBLE = 'possible'
LIMITED_LABEL = 'limited'
STRONG_LABEL = 'strong'

PRIMARY = 'primary'
ADDITIONAL = 'additional'

BY_PROFILE = 'profile'

ACADEMIC_ORDER = {STRONG: 0, MODERATE: 1, LOW: 2}
INTEREST_ORDER = {HIGH: 0, MEDIUM: 1, NOT_ASSESSED: 1, LOW: 2}
RIASEC_LABELS = dict(RiasecType.choices)


@dataclass(frozen=True)
class StudentInput:
    features: object
    interest: dict | None = None
    strand_group: str = ''
    program_code: str = ''


class RecommenderContext:
    """Schema, catalog, configuration and interest map, loaded once per request."""

    def __init__(self):
        self.schema = load_schema()
        self.candidates = load_candidates(self.schema)
        self.catalog = catalog_version(self.candidates)
        self.config_row, self.config = active_config()
        self.family_types = {}
        for row in FamilyInterestMap.objects.filter(family__is_active=True).select_related('family'):
            self.family_types.setdefault(row.family.code, []).append(row.riasec)
        self.domains = {}


@dataclass
class ProgramMatch:
    comparison: object
    academic: str
    interest: str
    interest_score: float | None
    ordered_by: str = BY_PROFILE
    family_rank: int = 0
    label: str = ''
    tier: str = ''
    neighbors: dict | None = None

    @property
    def candidate(self):
        return self.comparison.candidate


@dataclass
class Recommendation:
    ready: bool
    reason: str
    method: str
    items: list = field(default_factory=list)
    ranked: list = field(default_factory=list)
    comparisons: list = field(default_factory=list)
    family_order: list = field(default_factory=list)
    blocked: Counter = field(default_factory=Counter)
    not_evaluated: int = 0


def academic_tier(distance, config):
    cutoffs = config['academic_tiers']
    if distance <= cutoffs['strong']:
        return STRONG
    if distance <= cutoffs['moderate']:
        return MODERATE
    return LOW


def interest_tier(interest, types, config):
    """(tier, mean score) for a family's interest types; NOT_ASSESSED without scores or a mapping."""
    if not interest or not types:
        return NOT_ASSESSED, None
    score = round(sum(float(interest[letter]) for letter in types) / len(types), 2)
    cutoffs = config['interest_tiers']
    if score >= cutoffs['high']:
        return HIGH, score
    if score >= cutoffs['medium']:
        return MEDIUM, score
    return LOW, score


def profile_key(match):
    return (
        1 if match.comparison.unchecked_benchmarks else 0,
        len(match.comparison.below_benchmarks),
        ACADEMIC_ORDER[match.academic],
        INTEREST_ORDER[match.interest],
        round(match.comparison.distance, 6),
        0 if match.comparison.strand_context == TYPICAL else 1,
        match.candidate.name,
    )


def label_for(match, has_interest):
    comparison = match.comparison
    if comparison.evidence == LIMITED or comparison.unchecked_benchmarks or not has_interest:
        return LIMITED_LABEL
    capped = any(state == BELOW for state in comparison.benchmark_status.values())
    if not capped and match.academic == STRONG and match.interest == HIGH and match.family_rank <= 2:
        return STRONG_LABEL
    if not capped and match.academic in (STRONG, MODERATE) and match.interest in (HIGH, MEDIUM):
        return GOOD
    return POSSIBLE


def recommend(student, context):
    features = student.features
    comparisons = compare_all(features, context.candidates, student.strand_group, student.program_code)
    unevaluated = [row for row in comparisons if row.evidence == INSUFFICIENT]
    result = Recommendation(
        ready=False,
        reason='',
        method=METHOD,
        comparisons=comparisons,
        blocked=Counter(key for row in unevaluated for key in row.unobserved),
        not_evaluated=len(unevaluated),
    )
    if features.observed_count < MIN_SKILLS:
        result.reason = 'too_few_skills'
        return result
    if not context.candidates:
        result.reason = 'no_programs'
        return result

    config = context.config
    matches = []
    for row in comparisons:
        if not row.eligible:
            continue
        tier, score = interest_tier(student.interest, context.family_types.get(row.candidate.family_code), config)
        matches.append(ProgramMatch(row, academic_tier(row.distance, config), tier, score))
    if not matches:
        result.reason = 'no_evaluable'
        return result

    matches.sort(key=profile_key)

    order = []
    for match in matches:
        if match.candidate.family_code not in order:
            order.append(match.candidate.family_code)
    for match in matches:
        match.family_rank = order.index(match.candidate.family_code) + 1
        match.label = label_for(match, bool(student.interest))

    shortlist = config['shortlist']
    primary = matches[: shortlist['primary']]
    extra = [match for match in matches[shortlist['primary']:] if match.academic != LOW][: shortlist['additional']]
    for match in primary:
        match.tier = PRIMARY
    for match in extra:
        match.tier = ADDITIONAL
    result.items = primary + extra
    result.ranked = matches
    result.family_order = order
    result.ready = True
    return result


def evidence_for(match, recommendation, student, context):
    """Structured evidence for one program; explanations are rendered from this, never written freely."""
    comparison = match.comparison
    candidate = match.candidate
    label = context.schema.label
    strengths = sorted(
        (
            {
                'key': key,
                'label': label(key),
                'student': str(student.features.value(key)),
                'expected': str(candidate.levels[key]),
            }
            for key in comparison.observed
        ),
        key=lambda row: (-float(row['student']), row['label']),
    )
    below = [
        {
            'key': key,
            'label': label(key),
            'student': str(student.features.value(key)),
            'benchmark': str(candidate.benchmarks[key].value),
            'official': candidate.benchmarks[key].official,
            'source': candidate.benchmarks[key].source,
        }
        for key in comparison.below_benchmarks
    ]
    interest = None
    if match.interest != NOT_ASSESSED:
        types = [
            {'type': letter, 'label': RIASEC_LABELS[letter], 'score': student.interest[letter]}
            for letter in context.family_types.get(candidate.family_code, ())
        ]
        interest = {'tier': match.interest, 'score': match.interest_score, 'types': types}
    return {
        'method': match.ordered_by,
        'hybrid': False,
        'family': {
            'code': candidate.family_code,
            'name': candidate.family_name,
            'rank': match.family_rank,
            'ml_supported': False,
        },
        'academic': {'tier': match.academic, 'distance': round(comparison.distance, 2)},
        'strengths': strengths,
        'below_benchmark': below,
        'unchecked': [{'key': key, 'label': label(key)} for key in comparison.unobserved],
        'interest': interest,
        'strand': {'context': comparison.strand_context, 'group': student.strand_group},
        'coverage': {
            'status': comparison.evidence,
            'observed': len(comparison.observed),
            'total': comparison.total,
        },
        'neighbors': match.neighbors,
    }


def interest_profile(interest):
    """The six scores in Holland order, for display."""
    if not interest:
        return []
    return [{'type': letter, 'label': RIASEC_LABELS[letter], 'score': interest[letter]} for letter in RIASEC_ORDER]
