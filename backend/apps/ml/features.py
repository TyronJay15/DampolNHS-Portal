"""The one feature pipeline for academic ML (KDD stages marked below).

Selection      callers pick the grades a viewer may see (released for students,
               approved for staff); this module only reads what it is given.
Preprocessing  validate_grades(): drop scores outside 0-100 and duplicate rows.
Transformation transform(): subject -> SkillDomain (from the database) -> one
               fixed-length vector in schema order, with an observed mask.
               to_model_space(): the representation every model compares.

The schema is the ordered list of active SkillDomain rows, so a subject added
through the admin joins the vector as soon as it has a domain, with no code change.

Every valid grade ends in exactly one place, so none disappears silently:
  observed  its subject has an active domain: it counts toward that dimension
  excluded  its subject is marked matching_excluded: left out on purpose
  unmapped  its subject has no usable domain and no exclusion: a data gap to fix
A dimension with no grades stays unobserved (value None). It is never given a score.
"""

import hashlib
import math
from dataclasses import dataclass, field
from decimal import Decimal

from apps.grading.scores import average
from apps.school.models import SkillDomain, Subject

MIN_SCORE = Decimal('0')
MAX_SCORE = Decimal('100')


@dataclass(frozen=True)
class FeatureSchema:
    keys: tuple
    labels: tuple

    @property
    def version(self):
        return hashlib.sha1(','.join(self.keys).encode()).hexdigest()[:10]

    def label(self, key):
        return dict(zip(self.keys, self.labels)).get(key, key)


def load_schema():
    rows = SkillDomain.objects.filter(is_active=True).order_by('sort_order', 'key').values_list('key', 'label')
    return FeatureSchema(keys=tuple(key for key, _label in rows), labels=tuple(label for _key, label in rows))


@dataclass
class StudentFeatures:
    schema: FeatureSchema
    values: tuple
    observed: tuple
    counts: tuple
    overall: Decimal | None
    used: int
    excluded: tuple = ()
    unmapped: tuple = ()
    invalid: int = 0
    subjects: dict = field(default_factory=dict)

    @property
    def observed_count(self):
        return sum(self.observed)

    def value(self, key):
        index = self.schema.keys.index(key) if key in self.schema.keys else None
        if index is None or not self.observed[index]:
            return None
        return self.values[index]

    def averages(self):
        return {key: value for key, value, seen in zip(self.schema.keys, self.values, self.observed) if seen}


def validate_grades(grades):
    """Preprocessing: keep grades with a real subject and a score from 0 to 100, once each."""
    kept = []
    invalid = 0
    seen = set()
    for row in grades:
        if row is None:
            continue
        subject = getattr(row, 'subject', None)
        score = getattr(row, 'score', None)
        try:
            score = Decimal(str(score))
        except (ArithmeticError, TypeError, ValueError):
            score = None
        if subject is None or score is None or not score.is_finite() or not MIN_SCORE <= score <= MAX_SCORE:
            invalid += 1
            continue
        key = getattr(row, 'pk', None) or (getattr(row, 'subject_id', None), getattr(row, 'term_id', None), id(row))
        if key in seen:
            continue
        seen.add(key)
        kept.append((subject, score))
    return kept, invalid


def subject_domains(subject_ids, cache=None):
    """Map subject id -> (domain key, excluded flag) from the database, reusing a per-request cache."""
    cache = {} if cache is None else cache
    missing = [pk for pk in subject_ids if pk not in cache]
    if missing:
        rows = Subject.objects.filter(pk__in=missing).values_list('pk', 'skill_domain__key', 'matching_excluded')
        cache.update({pk: (key, excluded) for pk, key, excluded in rows})
    return cache


def transform(grades, schema=None, cache=None):
    schema = schema or load_schema()
    kept, invalid = validate_grades(grades)
    domains = subject_domains({subject.pk for subject, _score in kept}, cache)
    buckets = {key: [] for key in schema.keys}
    excluded = []
    unmapped = []
    subjects = {}
    for subject, score in kept:
        key, skip = domains.get(subject.pk, (None, False))
        if not skip and key in buckets:
            buckets[key].append(score)
            subjects.setdefault(key, []).append(subject.code)
            continue
        group = excluded if skip else unmapped
        if subject.code not in group:
            group.append(subject.code)
    values = tuple(average(buckets[key]) for key in schema.keys)
    return StudentFeatures(
        schema=schema,
        values=values,
        observed=tuple(bool(buckets[key]) for key in schema.keys),
        counts=tuple(len(buckets[key]) for key in schema.keys),
        overall=average([score for _subject, score in kept]),
        used=sum(len(rows) for rows in buckets.values()),
        excluded=tuple(excluded),
        unmapped=tuple(unmapped),
        invalid=invalid,
        subjects=subjects,
    )


def to_model_space(values, observed):
    """Relative strengths: each observed value minus the mean of the observed values.

    An unobserved dimension is 0, meaning "no evidence of being stronger or weaker
    than usual here". Every vector has len(schema) dimensions, so distances are
    always taken over the same space.
    """
    seen = [float(value) for value, flag in zip(values, observed) if flag]
    if not seen:
        return tuple(0.0 for _value in values)
    mean = sum(seen) / len(seen)
    return tuple(float(value) - mean if flag else 0.0 for value, flag in zip(values, observed))


def distance(left, right):
    if len(left) != len(right):
        raise ValueError('Feature vectors do not share a schema.')
    if not left:
        return 0.0
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)) / len(left))


RIASEC_ORDER = ('R', 'I', 'A', 'S', 'E', 'C')
STRAND_FEATURE = 'strand'


def model_feature_names(schema):
    """Numeric feature names in a fixed order, then the one categorical feature (the strand group)."""
    numeric = [name for key in schema.keys for name in (f'strength:{key}', f'observed:{key}')]
    numeric += ['overall'] + [f'interest:{letter}' for letter in RIASEC_ORDER]
    return numeric, [STRAND_FEATURE]


def model_features(features, interest, strand_group):
    """The machine-learning feature row for one student; training and live prediction both call this.

    Academic evidence is the relative-strength space (to_model_space) plus an explicit observed flag per
    domain, so a missing domain is marked as missing and is never read as a grade of 0. The caller must
    supply a completed interest assessment (six scores from 1 to 5).
    """
    row = {}
    space = to_model_space(features.values, features.observed)
    for key, value, seen in zip(features.schema.keys, space, features.observed):
        row[f'strength:{key}'] = value
        row[f'observed:{key}'] = 1.0 if seen else 0.0
    row['overall'] = float(features.overall) if features.overall is not None else 0.0
    for letter in RIASEC_ORDER:
        row[f'interest:{letter}'] = float(interest[letter])
    row[STRAND_FEATURE] = strand_group or ''
    return row
