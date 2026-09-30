"""College-course recommender baseline: nearest active CollegeProgram profiles in the shared feature space.

KDD data-mining and interpretation stages. This is the current baseline, not an
outcome-trained model: profiles are curated in the database, and no CollegeOutcome
records exist to learn from. outcome_dataset() builds the labeled rows a trained
model will use once real outcomes are recorded, through the same features.transform().

Missing data: every vector has one dimension per active SkillDomain (see
features.to_model_space), and an unobserved dimension is neutral (0), never a score.
compare_all() is the single path behind both the ranking and the diagnostics.

Similarity and evidence are separate. Similarity is the distance. Evidence is how
much of a program's own profile the student has real grades for:
  coverage      = program skill areas with student grades / all program skill areas
  strong        coverage >= settings.MIN_RECOMMENDATION_EVIDENCE_COVERAGE
  limited       some coverage, below the threshold: comparable, but under-supported
  insufficient  a required minimum cannot be checked (no grade there), or no
                program skill area has grades: not presented as a recommendation
A minimum with no grade behind it is "unknown", never "passed". Evidence never
changes the distance or the order; it decides what may be shown and how it is labeled.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import NamedTuple

from django.conf import settings

from apps.grading.models import Grade
from apps.ml.features import distance, load_schema, to_model_space, transform
from apps.ml.models import CollegeOutcome, CollegeProgram

METHOD = 'profile_similarity'
RESULTS = 3
TRACK_BOOST = 0.85
RANKED = 'ranked'
NEEDS_DATA = 'needs_data'
BELOW_MINIMUM = 'below_minimum'
PASSED = 'passed'
FAILED = 'failed'
UNKNOWN = 'unknown'
STRONG = 'strong'
LIMITED = 'limited'
INSUFFICIENT = 'insufficient'


@dataclass(frozen=True)
class Candidate:
    code: str
    name: str
    levels: dict
    minimums: dict
    shs_codes: frozenset
    vector: tuple


@dataclass(frozen=True)
class Comparison:
    """One student against one college program."""

    candidate: Candidate
    status: str
    distance: float
    track_match: bool
    minimum_status: dict
    observed: tuple
    unobserved: tuple
    imputed_share: float
    evidence: str

    @property
    def total(self):
        return len(self.observed) + len(self.unobserved)

    @property
    def coverage(self):
        return len(self.observed) / self.total if self.total else 0.0

    @property
    def missing_minimums(self):
        return tuple(key for key, state in self.minimum_status.items() if state == UNKNOWN)

    @property
    def below_minimums(self):
        return tuple(key for key, state in self.minimum_status.items() if state == FAILED)

    @property
    def eligible(self):
        """May be presented as a recommendation: minimums met, and some real evidence behind it."""
        return self.status == RANKED and self.evidence != INSUFFICIENT


def evidence_threshold():
    return float(settings.MIN_RECOMMENDATION_EVIDENCE_COVERAGE)


def load_candidates(schema):
    rows = (
        CollegeProgram.objects.filter(is_active=True)
        .prefetch_related('skills__domain', 'shs_programs')
        .order_by('sort_order', 'code')
    )
    candidates = []
    for program in rows:
        # A program's relevant domains are its profile rows inside the active schema.
        skills = [skill for skill in program.skills.all() if skill.domain.key in schema.keys]
        levels = {skill.domain.key: skill.level for skill in skills}
        minimums = {skill.domain.key: skill.minimum for skill in skills if skill.minimum is not None}
        candidates.append(
            Candidate(
                code=program.code,
                name=program.name,
                levels=levels,
                minimums=minimums,
                shs_codes=frozenset(item.code for item in program.shs_programs.all()),
                vector=to_model_space(
                    tuple(levels.get(key) for key in schema.keys),
                    tuple(key in levels for key in schema.keys),
                ),
            )
        )
    return candidates


def catalog_version(candidates):
    parts = [
        f'{row.code}:{sorted(row.levels.items())}:{sorted(row.minimums.items())}:{sorted(row.shs_codes)}'
        for row in candidates
    ]
    return hashlib.sha1('|'.join(parts).encode()).hexdigest()[:10]


def compare_all(features, candidates, program_code=None):
    """Compare a student with every candidate. Ranking and diagnostics both read this."""
    student = to_model_space(features.values, features.observed)
    threshold = evidence_threshold()
    comparisons = []
    for candidate in candidates:
        minimum_status = {
            key: UNKNOWN if features.value(key) is None else PASSED if features.value(key) >= minimum else FAILED
            for key, minimum in candidate.minimums.items()
        }
        states = set(minimum_status.values())
        status = NEEDS_DATA if UNKNOWN in states else BELOW_MINIMUM if FAILED in states else RANKED
        observed = tuple(key for key in candidate.levels if features.value(key) is not None)
        unobserved = tuple(key for key in candidate.levels if features.value(key) is None)
        coverage = len(observed) / len(candidate.levels) if candidate.levels else 0.0
        if status == NEEDS_DATA or not observed:
            evidence = INSUFFICIENT
        else:
            evidence = STRONG if round(coverage, 4) >= threshold else LIMITED
        track_match = bool(program_code and program_code in candidate.shs_codes)
        squares = [(left - right) ** 2 for left, right in zip(student, candidate.vector)]
        total = sum(squares)
        imputed = sum(square for square, seen in zip(squares, features.observed) if not seen)
        comparisons.append(
            Comparison(
                candidate=candidate,
                status=status,
                distance=distance(student, candidate.vector) * (TRACK_BOOST if track_match else 1),
                track_match=track_match,
                minimum_status=minimum_status,
                observed=observed,
                unobserved=unobserved,
                imputed_share=imputed / total if total else 0.0,
                evidence=evidence,
            )
        )
    return comparisons


def _reason(features, comparison):
    """States what was compared. It does not claim a match; the distance decides that."""
    parts = [f'{features.schema.label(key)} ({features.value(key)})' for key in comparison.observed]
    return f'Compared on your grades in {" and ".join(parts)}.'


class Ranking(NamedTuple):
    """What rank() returns. Callers read it by field name, so adding a field never breaks them."""

    courses: list
    blocked: Counter
    not_evaluated: int


def rank(features, candidates, program_code=None, limit=RESULTS):
    """Return a Ranking: courses to show, domain keys that would unlock more programs, programs not evaluated.

    Order is by distance alone. Evidence only decides whether a program may be shown.
    """
    comparisons = compare_all(features, candidates, program_code)
    unevaluated = [row for row in comparisons if row.evidence == INSUFFICIENT]
    blocked = Counter(key for row in unevaluated for key in (row.missing_minimums or row.unobserved))
    eligible = sorted(
        (row for row in comparisons if row.eligible),
        key=lambda row: (row.distance, row.candidate.name),
    )
    label = features.schema.label
    ranked = [
        {
            'code': row.candidate.code,
            'name': row.candidate.name,
            'distance': round(row.distance, 2),
            'reason': _reason(features, row),
            'track_match': row.track_match,
            'evidence': {
                'status': row.evidence,
                'observed': len(row.observed),
                'total': row.total,
                'coverage': round(100 * row.coverage, 2),
                'observed_domains': [label(key) for key in row.observed],
                'missing_domains': [label(key) for key in row.unobserved],
            },
        }
        for row in eligible[:limit]
    ]
    return Ranking(courses=ranked, blocked=blocked, not_evaluated=len(unevaluated))


def outcome_dataset(schema=None):
    """Labeled rows for a future outcome-trained model. Empty until real outcomes are recorded.

    Each recorded graduate becomes one row: the feature vector from their approved
    and released grades (the same transform live students go through) and the
    college program they actually entered as the label.
    """
    schema = schema or load_schema()
    cache = {}
    rows = []
    for outcome in CollegeOutcome.objects.select_related('college_program').order_by('pk'):
        grades = Grade.objects.filter(
            student_id=outcome.student_id,
            status__in=[Grade.Status.APPROVED, Grade.Status.RELEASED],
        ).select_related('subject')
        features = transform(grades, schema, cache)
        rows.append(
            {
                'student': outcome.student_id,
                'label': outcome.college_program.code,
                'observed': features.observed,
                'vector': to_model_space(features.values, features.observed),
            }
        )
    return rows
