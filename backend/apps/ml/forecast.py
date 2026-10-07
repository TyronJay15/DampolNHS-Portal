"""Grade 11 next-intake trend: one LinearRegression per program, trained on completed years only.

KDD stages, as shown on the Admin planning page:
  Selection       ClusterSnapshot rows of completed (archived) years, written when a year is archived.
  Preprocessing   only years run under the program's own Grade 11 curriculum; other curricula excluded.
  Transformation  one series per program: x = school-year position, y = valid Grade 11 applicants.
  Data mining     apps.ml.regression.fit_line (scikit-learn LinearRegression).
  Evaluation      forward in time against "same as last year"; a trend that does not beat it is low confidence.
  Knowledge       next year's expected applicants per program, sections needed, trend direction.

Gate: the trend stays locked until MIN_YEARS completed years exist under the current Grade 11 curriculum.
Until then the page shows an estimate (same as this or the last completed year), never a forecast.
Training runs only from the Retrain button, the train_forecast command or archiving a year. Page requests
read the stored ModelRun and never train or write.
"""

from apps.audit import services as audit
from apps.ml.models import ClusterSnapshot
from apps.ml.regression import forward_tests, fit_line, mae, predict_line, rmse
from apps.ml.store import last_run, save_run
from apps.school.curriculum import curriculum_for, freeze_year
from apps.school.forecast import DEFAULT_CAPACITY, GRADE_11, enrollment_counts, grade11_programs, sections_needed
from apps.school.models import Program, SchoolYear

MIN_YEARS = 3
FEATURE_SCHEMA = {
    'x': 'school_year_index',
    'y': 'grade11_applied_count',
    'group': 'program',
    'model': 'sklearn.LinearRegression',
    'version': 2,
}
CONFIDENT = 'confident'
LOW_CONFIDENCE = 'low_confidence'
UNTESTED = 'untested'
STEADY_SLOPE = 0.5  # applicants per year; smaller changes read as steady


def snapshot_year(year):
    """Store (or refresh) one year's final Grade 11 counts per program, with that year's curriculum."""
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
                'is_synthetic': False,
            },
        )
        rows.append(snapshot)
    return rows


def ensure_snapshots():
    """Snapshot completed years that have none yet. Existing history is never overwritten here."""
    missing = SchoolYear.objects.filter(archived_at__isnull=False, cluster_snapshots__isnull=True)
    for year in missing.order_by('label'):
        snapshot_year(year)


def applicable_curriculum():
    """The Grade 11 curriculum the trend is for: the current year's."""
    return curriculum_for(SchoolYear.objects.filter(is_current=True).first(), GRADE_11)


def completed_years(curriculum):
    """Archived years whose Grade 11 ran under `curriculum`, oldest first. Read-only."""
    if curriculum is None:
        return []
    years = SchoolYear.objects.filter(archived_at__isnull=False).order_by('label')
    return [year.label for year in years if getattr(curriculum_for(year, GRADE_11), 'pk', None) == curriculum.pk]


def _series(index):
    """Per program: [(x, applied)] from completed years under the program's own curriculum."""
    series, synthetic = {}, False
    rows = ClusterSnapshot.objects.filter(program__isnull=False, school_year__archived_at__isnull=False).select_related(
        'program'
    )
    for row in rows:
        if row.program.grade_level != GRADE_11 or row.curriculum_id != row.program.curriculum_id:
            continue
        series.setdefault(row.program_id, []).append((index[row.school_year_id], row.applied_count))
        synthetic = synthetic or row.is_synthetic
    return {pk: sorted(points) for pk, points in series.items()}, synthetic


def _program_model(program, points, labels):
    line = fit_line(*zip(*points))
    tests = forward_tests(points, MIN_YEARS)
    model_errors = [test['predicted'] - test['actual'] for test in tests]
    baseline_errors = [test['baseline'] - test['actual'] for test in tests]
    model_rmse, baseline_rmse = rmse(model_errors), rmse(baseline_errors)
    if not tests:
        status = UNTESTED
    else:
        status = CONFIDENT if model_rmse < baseline_rmse else LOW_CONFIDENCE
    return {
        **line,
        'code': program.code,
        'years': [labels[x] for x, _y in points],
        'tests': len(tests),
        'rmse': _round(model_rmse),
        'baseline_rmse': _round(baseline_rmse),
        'status': status,
    }, model_errors, baseline_errors


def _round(value):
    return None if value is None else round(value, 3)


def _evaluation(model_errors, baseline_errors, tested_programs):
    if not model_errors:
        return {
            'evaluated': False,
            'reason': f'Needs {MIN_YEARS + 1} completed years for a program before a year can be predicted from earlier ones.',
        }
    return {
        'evaluated': True,
        'programs': tested_programs,
        'tests': len(model_errors),
        'mae': _round(mae(model_errors)),
        'rmse': _round(rmse(model_errors)),
        'baseline_mae': _round(mae(baseline_errors)),
        'baseline_rmse': _round(rmse(baseline_errors)),
        'beats_baseline': rmse(model_errors) < rmse(baseline_errors),
        'note': 'Measured on very few years, so treat it as limited evidence.' if len(model_errors) < 5 else '',
    }


def train_forecast():
    """Fit one trend per eligible program, evaluate it forward in time, and save a ModelRun."""
    ensure_snapshots()
    years = list(SchoolYear.objects.order_by('label'))
    index = {year.pk: position for position, year in enumerate(years)}
    labels = [year.label for year in years]
    series, synthetic = _series(index)
    curriculum = applicable_curriculum()
    completed = completed_years(curriculum)
    unlocked = len(completed) >= MIN_YEARS
    programs = {row.pk: row for row in Program.objects.filter(pk__in=series)}

    models, model_errors, baseline_errors, tested = {}, [], [], 0
    if unlocked:
        for pk, points in series.items():
            if len(points) < MIN_YEARS:
                continue
            model, errors, baseline = _program_model(programs[pk], points, labels)
            models[str(pk)] = model
            model_errors += errors
            baseline_errors += baseline
            tested += bool(errors)
    snapshots = ClusterSnapshot.objects.filter(program__isnull=False, school_year__archived_at__isnull=False)
    return save_run(
        name='forecast',
        algorithm='sklearn_linear_regression',
        n_train=sum(len(points) for points in series.values()),
        n_test=len(model_errors),
        metrics={
            'ready': bool(models),
            'min_years': MIN_YEARS,
            'completed_years': len(completed),
            'completed_labels': completed,
            'curriculum': curriculum.code if curriculum else None,
            'years': labels,
            'evaluation': _evaluation(model_errors, baseline_errors, tested),
            'synthetic': synthetic,
        },
        artifact={'schema': FEATURE_SCHEMA['version'], 'years': labels, 'models': models, 'synthetic': synthetic},
        feature_schema=FEATURE_SCHEMA,
        curriculum_scope=sorted(
            set(snapshots.exclude(curriculum__isnull=True).values_list('curriculum__code', flat=True))
        ),
        dataset={
            'snapshots': snapshots.count(),
            'programs': len(series),
            'years': len(years),
            'completed_years': _archived_labels(),
        },
    )


def retrain(user, reason=''):
    """Train and record who did it and why, in the audit log. Used by the Retrain button and archiving."""
    run = train_forecast()
    audit.record(
        user=user,
        action='model_trained',
        summary=f'Retrained the enrollment forecast (v{run.version}){f" {reason}" if reason else ""}',
        target_type='ModelRun',
        target_id=run.id,
        details={'ready': run.metrics.get('ready'), 'completed_years': run.metrics.get('completed_years')},
    )
    return run


def _archived_labels():
    return list(SchoolYear.objects.filter(archived_at__isnull=False).order_by('label').values_list('label', flat=True))


def is_stale(run):
    """True when school years were archived or restored after this model was trained."""
    return run is not None and (run.dataset or {}).get('completed_years') != _archived_labels()


def _usable(run):
    """A saved forecast is usable only if it was trained with the current feature schema."""
    if run is None:
        return False, ''
    if run.feature_schema != FEATURE_SCHEMA or (run.artifact or {}).get('schema') != FEATURE_SCHEMA['version']:
        return False, 'The saved forecast uses an older format. Retrain it to refresh.'
    return True, ''


def _gate(curriculum, current_label):
    completed = completed_years(curriculum)
    missing = max(0, MIN_YEARS - len(completed))
    name = curriculum.name if curriculum else 'the current curriculum'
    if missing:
        note = (
            f'{missing} more completed school year{"s" if missing != 1 else ""} under {name} '
            f'{"are" if missing != 1 else "is"} needed. A year counts once it is archived'
            f'{f", so {current_label} counts after it ends" if current_label else ""}.'
        )
    else:
        note = ''
    archived = SchoolYear.objects.filter(archived_at__isnull=False).count()
    return {
        'completed_years': len(completed),
        'required_years': MIN_YEARS,
        'completed_labels': completed,
        'other_curriculum_years': archived - len(completed),
        'unlock_note': note,
    }


def _last_completed_applied(program_id):
    row = (
        ClusterSnapshot.objects.filter(program_id=program_id, school_year__archived_at__isnull=False)
        .order_by('-school_year__label')
        .values_list('applied_count', flat=True)
        .first()
    )
    return row


def _direction(slope):
    if slope > STEADY_SLOPE:
        return 'rising'
    if slope < -STEADY_SLOPE:
        return 'falling'
    return 'steady'


def attach_attractiveness(payload):
    """Add next year's Grade 11 intake per program and the trend model's status. Read-only.

    With an unlocked, trained trend the intake is a model forecast with its confidence; otherwise it is an
    estimate equal to this year's applicants (or the last completed year's), labelled as such.
    """
    run = last_run('forecast')
    usable, reason = _usable(run)
    artifact = (run.artifact or {}) if usable else {}
    metrics = (run.metrics or {}) if usable else {}
    curriculum = applicable_curriculum()
    year_label = payload.get('school_year')
    gate = _gate(curriculum, year_label)
    models = (artifact.get('models') or {}) if gate['completed_years'] >= MIN_YEARS else {}
    labels = artifact.get('years') or []
    next_index = labels.index(year_label) + 1 if year_label in labels else None
    capacity = payload.get('typical_capacity') or DEFAULT_CAPACITY

    clusters = []
    for row in payload.get('clusters') or []:
        model = models.get(str(row['program_id']))
        projected = None
        if model and next_index is not None:
            projected = max(round(predict_line(model, next_index)), 0)
        if projected is not None:
            intake, basis, note = projected, 'forecast', ''
        elif row['applied']:
            intake, basis, note = row['applied'], 'estimate', 'same as this year'
        else:
            last = _last_completed_applied(row['program_id'])
            intake, basis, note = (last, 'estimate', 'same as the last completed year') if last else (0, 'estimate', 'no data yet')
        clusters.append(
            {
                **row,
                'slope': round(float(model['slope']), 3) if model else 0,
                'r2': round(float(model['r2']), 3) if model else 0,
                'direction': _direction(float(model['slope'])) if model else None,
                'trend_status': model['status'] if model else 'locked',
                'trend_years': model['years'] if model else [],
                'projected': projected,
                'projected_basis': 'forecast' if projected is not None else None,
                'next_intake': intake,
                'next_intake_basis': basis,
                'next_intake_note': note,
                'sections_needed': sections_needed(intake, capacity),
            }
        )
    forecasted = any(row['projected'] is not None for row in clusters)
    if not forecasted and not reason:
        reason = gate['unlock_note'] or 'No program has enough completed years for a trend yet.'
    most = max(clusters, key=lambda row: row['applied'], default=None)
    payload.update(
        {
            'clusters': clusters,
            'method': 'linear_regression' if forecasted else 'counts',
            'ready': forecasted,
            'ready_reason': '' if forecasted else reason,
            'trend': {
                **gate,
                'curriculum': {'code': curriculum.code, 'name': curriculum.name} if curriculum else None,
                'status': 'ready' if forecasted else 'locked',
                'synthetic': bool(metrics.get('synthetic')) if forecasted else False,
            },
            'grade11_sections_next_year': sum(row['sections_needed'] for row in clusters),
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
                    'evaluation': metrics.get('evaluation'),
                    'stale': is_stale(run),
                }
                if usable
                else None
            ),
        }
    )
    return payload
