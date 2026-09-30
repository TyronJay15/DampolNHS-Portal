"""Grade 11 enrollment forecast: one linear trend per program, fit on yearly snapshots.

Training reads ClusterSnapshot history of completed (archived) years only, so a year
still enrolling never drags the trend down. Each snapshot records the Grade 11
curriculum in force that year; a trend only uses years run under the program's own
curriculum, so no new-curriculum history is invented. Prediction reads the saved
ModelRun artifact; it never trains or writes during a request.
"""

import math

from apps.ml.models import ClusterSnapshot
from apps.ml.regression import fit_line, predict_line
from apps.ml.store import last_run, save_run
from apps.school.curriculum import curriculum_for, freeze_year
from apps.school.forecast import DEFAULT_CAPACITY, GRADE_11, enrollment_counts, grade11_programs, sections_needed
from apps.school.models import SchoolYear

MIN_YEARS = 3
FEATURE_SCHEMA = {'x': 'school_year_index', 'y': 'grade11_applied_count', 'group': 'program'}
NOT_READY = f'Needs {MIN_YEARS} completed school years in the same curriculum to train Linear Regression.'


def snapshot_year(year):
    """Store one year's observed Grade 11 counts per program, tagged with that year's Grade 11 curriculum."""
    freeze_year(year)
    curriculum = curriculum_for(year, GRADE_11)
    counts = enrollment_counts(year)
    rows = []
    for program in grade11_programs(year, counts):
        row = counts.get(program.pk, {'applied': 0, 'approved': 0})
        snapshot, _created = ClusterSnapshot.objects.update_or_create(
            school_year=year,
            cluster_code=program.code,
            defaults={
                'program': program,
                'curriculum': curriculum,
                'applied_count': row['applied'],
                'approved_count': row['approved'],
            },
        )
        rows.append(snapshot)
    return rows


def snapshot_all_years():
    return [snapshot_year(year) for year in SchoolYear.objects.all().order_by('label')]


def _series(index):
    """Preprocessing: completed years only, Grade 11 programs, snapshots under the program's own curriculum."""
    series = {}
    rows = ClusterSnapshot.objects.filter(program__isnull=False, school_year__archived_at__isnull=False).select_related(
        'program'
    )
    for row in rows:
        if row.program.grade_level != GRADE_11 or row.curriculum_id != row.program.curriculum_id:
            continue
        series.setdefault(row.program_id, []).append((index[row.school_year_id], row.applied_count))
    return {pk: sorted(points) for pk, points in series.items()}


def _holdout(series):
    """Fit without each program's latest year, then score the prediction for that year."""
    errors = []
    for points in series.values():
        if len(points) < MIN_YEARS + 1:
            continue
        model = fit_line(*zip(*points[:-1]))
        x, y = points[-1]
        errors.append(predict_line(model, x) - y)
    if not errors:
        return {
            'evaluated': False,
            'reason': f'Needs {MIN_YEARS + 1} school years for a program to hold out its latest year.',
        }
    return {
        'evaluated': True,
        'programs': len(errors),
        'mae': round(sum(abs(error) for error in errors) / len(errors), 3),
        'rmse': round(math.sqrt(sum(error**2 for error in errors) / len(errors)), 3),
    }


def train_forecast():
    snapshot_all_years()
    years = list(SchoolYear.objects.order_by('label'))
    index = {year.pk: position for position, year in enumerate(years)}
    series = _series(index)
    models = {str(pk): fit_line(*zip(*points)) for pk, points in series.items() if len(points) >= MIN_YEARS}
    evaluation = _holdout(series)
    snapshots = ClusterSnapshot.objects.filter(program__isnull=False, school_year__archived_at__isnull=False)
    return save_run(
        name='forecast',
        algorithm='linear_regression',
        n_train=sum(len(points) for points in series.values()),
        n_test=evaluation.get('programs', 0),
        metrics={
            'ready': bool(models),
            'min_years': MIN_YEARS,
            'years': [year.label for year in years],
            'evaluation': evaluation,
        },
        artifact={'models': models, 'years': [year.label for year in years]},
        feature_schema=FEATURE_SCHEMA,
        curriculum_scope=sorted(
            set(snapshots.exclude(curriculum__isnull=True).values_list('curriculum__code', flat=True))
        ),
        dataset={
            'snapshots': snapshots.count(),
            'programs': len(series),
            'years': len(years),
            'completed_years': _completed_years(),
        },
    )


def _completed_years():
    return list(SchoolYear.objects.filter(archived_at__isnull=False).order_by('label').values_list('label', flat=True))


def is_stale(run):
    """True when school years were archived or restored after this model was trained."""
    return run is not None and (run.dataset or {}).get('completed_years') != _completed_years()


def _usable(run):
    """A saved forecast is usable only if it was trained with the current feature schema."""
    if run is None:
        return False, NOT_READY
    if run.feature_schema != FEATURE_SCHEMA or 'years' not in (run.artifact or {}):
        return False, 'The saved forecast uses an older format. Retrain it to refresh.'
    return True, ''


def attach_attractiveness(payload):
    """Add next year's Grade 11 intake per cluster to the observed payload. Read-only.

    With a trained trend the intake is a forecast; without one it is this year's
    applicants, labeled as an estimate.
    """
    run = last_run('forecast')
    usable, reason = _usable(run)
    artifact = (run.artifact or {}) if usable else {}
    models = artifact.get('models') or {}
    labels = artifact.get('years') or []
    year_label = payload.get('school_year')
    next_index = labels.index(year_label) + 1 if year_label in labels else None
    capacity = payload.get('typical_capacity') or DEFAULT_CAPACITY

    clusters = []
    for row in payload.get('clusters') or []:
        model = models.get(str(row['program_id']))
        projected = None
        if model and next_index is not None:
            projected = max(round(predict_line(model, next_index)), 0)
        intake = projected if projected is not None else row['applied']
        clusters.append(
            {
                **row,
                'slope': round(float(model['slope']), 3) if model else 0,
                'r2': round(float(model['r2']), 3) if model else 0,
                'projected': projected,
                'projected_basis': 'forecast' if projected is not None else None,
                'next_intake': intake,
                'next_intake_basis': 'forecast' if projected is not None else 'estimate',
                'sections_needed': sections_needed(intake, capacity),
            }
        )
    forecasted = any(row['projected'] is not None for row in clusters)
    if usable and not forecasted:
        reason = NOT_READY
    most = max(clusters, key=lambda row: row['applied'], default=None)
    payload.update(
        {
            'clusters': clusters,
            'method': 'linear_regression' if forecasted else 'counts',
            'ready': forecasted,
            'ready_reason': '' if forecasted else reason,
            'most_applied': (
                {'code': most['code'], 'name': most['name'], 'applied': most['applied']}
                if most and most['applied']
                else None
            ),
            'model': (
                {
                    'name': run.name,
                    'version': run.version,
                    'trained_at': run.trained_at,
                    'evaluation': (run.metrics or {}).get('evaluation'),
                    'stale': is_stale(run),
                }
                if usable
                else None
            ),
        }
    )
    return payload
