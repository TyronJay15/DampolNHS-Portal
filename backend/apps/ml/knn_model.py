"""Profile matching: compare a student with every active college program profile.

This is the knowledge-based method of the recommender (KDD data-mining stage). Profiles are validated
reference data in the database, not learned from outcomes. apps.ml.recommender orders and labels the
comparisons; this module only measures them, so ranking and diagnostics always share one comparison.

Missing data: every vector has one dimension per active SkillDomain (see features.to_model_space), and
an unobserved dimension is neutral (0) for distance only, never a score.

Similarity, evidence and benchmarks are separate:
  distance   root-mean-square difference of relative strengths, every domain weighted equally
  evidence   share of the program's skill areas backed by the student's real grades
               strong        coverage >= settings.MIN_RECOMMENDATION_EVIDENCE_COVERAGE
               limited       some coverage, below the threshold
               insufficient  no program skill area has a grade: the program cannot be evaluated
  benchmarks a profile benchmark is guidance; MET, BELOW or UNKNOWN (no grade). A benchmark never
             removes a program. An UNKNOWN benchmark means the program's key area cannot be checked
             yet, so the recommender places it after programs that can be. Only a sourced OFFICIAL
             requirement may be shown as a requirement, and even then the program stays visible.
  strand     context only: TYPICAL when the program usually follows the student's strand. It never
             changes the distance. The recommender uses it only as a last tie-break, never as a gate.
"""

import hashlib
from dataclasses import dataclass

from django.conf import settings

from apps.ml.features import distance, to_model_space
from apps.ml.models import CollegeProgram, CollegeProgramSkill

METHOD = 'profile_matching'
MET = 'met'
BELOW = 'below'
UNKNOWN = 'unknown'
STRONG = 'strong'
LIMITED = 'limited'
INSUFFICIENT = 'insufficient'
TYPICAL = 'typical'
OTHER = 'other'


@dataclass(frozen=True)
class Benchmark:
    value: object
    official: bool
    source: str


@dataclass(frozen=True)
class Candidate:
    pk: int
    code: str
    name: str
    family_code: str
    family_name: str
    levels: dict
    benchmarks: dict
    shs_codes: frozenset
    strand_groups: frozenset
    vector: tuple


@dataclass(frozen=True)
class Comparison:
    """One student against one college program."""

    candidate: Candidate
    distance: float
    benchmark_status: dict
    observed: tuple
    unobserved: tuple
    imputed_share: float
    evidence: str
    strand_context: str

    @property
    def total(self):
        return len(self.observed) + len(self.unobserved)

    @property
    def coverage(self):
        return len(self.observed) / self.total if self.total else 0.0

    @property
    def below_benchmarks(self):
        return tuple(key for key, state in self.benchmark_status.items() if state == BELOW)

    @property
    def unchecked_benchmarks(self):
        return tuple(key for key, state in self.benchmark_status.items() if state == UNKNOWN)

    @property
    def official_unmet(self):
        return tuple(key for key in self.below_benchmarks if self.candidate.benchmarks[key].official)

    @property
    def eligible(self):
        """Can be evaluated and shown: at least one of its skill areas has a real grade."""
        return self.evidence != INSUFFICIENT


def evidence_threshold():
    return float(settings.MIN_RECOMMENDATION_EVIDENCE_COVERAGE)


def load_candidates(schema):
    rows = (
        CollegeProgram.objects.filter(is_active=True)
        .exclude(family__is_active=False)
        .select_related('family')
        .prefetch_related('skills__domain', 'shs_programs')
        .order_by('sort_order', 'code')
    )
    candidates = []
    for program in rows:
        # A program's relevant domains are its profile rows inside the active schema.
        skills = [skill for skill in program.skills.all() if skill.domain.key in schema.keys]
        levels = {skill.domain.key: skill.level for skill in skills}
        benchmarks = {
            skill.domain.key: Benchmark(
                value=skill.minimum,
                official=skill.minimum_kind == CollegeProgramSkill.MinimumKind.OFFICIAL,
                source=skill.requirement_source,
            )
            for skill in skills
            if skill.minimum is not None
        }
        linked = list(program.shs_programs.all())
        candidates.append(
            Candidate(
                pk=program.pk,
                code=program.code,
                name=program.name,
                family_code=program.family.code if program.family_id else '',
                family_name=program.family.name if program.family_id else '',
                levels=levels,
                benchmarks=benchmarks,
                shs_codes=frozenset(item.code for item in linked),
                strand_groups=frozenset(item.strand_group for item in linked if item.strand_group),
                vector=to_model_space(
                    tuple(levels.get(key) for key in schema.keys),
                    tuple(key in levels for key in schema.keys),
                ),
            )
        )
    return candidates


def catalog_version(candidates):
    parts = [
        f'{row.code}:{row.family_code}:{sorted(row.levels.items())}:'
        f'{sorted((key, item.value, item.official) for key, item in row.benchmarks.items())}:{sorted(row.shs_codes)}'
        for row in candidates
    ]
    return hashlib.sha1('|'.join(parts).encode()).hexdigest()[:10]


def strand_context(candidate, strand_group='', program_code=''):
    """TYPICAL when the program usually follows the student's strand, OTHER when it usually follows another,
    and '' when the catalog or the student gives nothing to compare."""
    if not candidate.shs_codes or not (strand_group or program_code):
        return ''
    if program_code in candidate.shs_codes or (strand_group and strand_group in candidate.strand_groups):
        return TYPICAL
    return OTHER


def compare_all(features, candidates, strand_group='', program_code=''):
    """Compare a student with every candidate. Ranking and diagnostics both read this."""
    student = to_model_space(features.values, features.observed)
    threshold = evidence_threshold()
    comparisons = []
    for candidate in candidates:
        benchmark_status = {
            key: UNKNOWN if features.value(key) is None else MET if features.value(key) >= item.value else BELOW
            for key, item in candidate.benchmarks.items()
        }
        observed = tuple(key for key in candidate.levels if features.value(key) is not None)
        unobserved = tuple(key for key in candidate.levels if features.value(key) is None)
        coverage = len(observed) / len(candidate.levels) if candidate.levels else 0.0
        if not observed:
            evidence = INSUFFICIENT
        else:
            evidence = STRONG if round(coverage, 4) >= threshold else LIMITED
        squares = [(left - right) ** 2 for left, right in zip(student, candidate.vector)]
        total = sum(squares)
        imputed = sum(square for square, seen in zip(squares, features.observed) if not seen)
        comparisons.append(
            Comparison(
                candidate=candidate,
                distance=distance(student, candidate.vector),
                benchmark_status=benchmark_status,
                observed=observed,
                unobserved=unobserved,
                imputed_share=imputed / total if total else 0.0,
                evidence=evidence,
                strand_context=strand_context(candidate, strand_group, program_code),
            )
        )
    return comparisons
