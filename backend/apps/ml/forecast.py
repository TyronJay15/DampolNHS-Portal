from collections import Counter

from apps.ml.models import ClusterSnapshot
from apps.ml.regression import fit_line, predict_line
from apps.ml.store import last_run, save_run
from apps.people.models import Registration
from apps.school.models import SchoolYear
from apps.school.program_catalog import GRADE11_TO_GRADE12

CLUSTERS = tuple(GRADE11_TO_GRADE12)
MIN_YEARS = 3


def _counts(year):
    rows = Registration.objects.filter(school_year=year, grade_level_enrollment='Grade 11')
    applied = Counter(rows.exclude(status=Registration.Status.REJECTED).values_list('program__code', flat=True))
    approved = Counter(rows.filter(status=Registration.Status.APPROVED).values_list('program__code', flat=True))
    return applied, approved


def snapshot_year(year):
    applied, approved = _counts(year)
    rows = []
    for code in CLUSTERS:
        row, _created = ClusterSnapshot.objects.update_or_create(
            school_year=year,
            cluster_code=code,
            defaults={'applied_count': applied.get(code, 0), 'approved_count': approved.get(code, 0)},
        )
        rows.append(row)
    return rows


def snapshot_all_years():
    return [snapshot_year(year) for year in SchoolYear.objects.all().order_by('label')]


def train_forecast():
    snapshot_all_years()
    years = list(SchoolYear.objects.order_by('label'))
    series = {code: [] for code in CLUSTERS}
    for index, year in enumerate(years):
        for row in year.cluster_snapshots.all():
            series.setdefault(row.cluster_code, []).append((index, row.applied_count))
    ready = len(years) >= MIN_YEARS
    models = {code: fit_line(*zip(*points)) if points else fit_line([], []) for code, points in series.items()}
    return save_run(
        name='forecast',
        algorithm='linear_regression',
        n_train=len(years),
        n_test=0,
        metrics={'ready': ready, 'min_years': MIN_YEARS, 'years': [year.label for year in years]},
        artifact={'models': models, 'next_index': len(years)},
    )


def attach_attractiveness(payload):
    run = last_run('forecast')
    artifact = (run.artifact if run else {}) or {}
    models = artifact.get('models') or {}
    ready = bool(run and run.metrics.get('ready'))
    year = SchoolYear.objects.filter(label=payload.get('school_year')).first()
    applied = {}
    if year:
        snapshot_year(year)
        applied = {row.cluster_code: row.applied_count for row in year.cluster_snapshots.all()}
    ranked = sorted(CLUSTERS, key=lambda code: (-applied.get(code, 0), code))
    clusters = []
    for row in payload.get('clusters') or []:
        model = models.get(row['code']) or {}
        projected = round(predict_line(model, artifact.get('next_index', 0))) if ready and model else None
        clusters.append(
            {
                **row,
                'applied': applied.get(row['code'], row.get('count', 0)),
                'rank': ranked.index(row['code']) + 1 if row['code'] in ranked else None,
                'slope': round(float(model.get('slope', 0)), 3) if model else 0,
                'r2': round(float(model.get('r2', 0)), 3) if model else 0,
                'projected': max(projected, 0) if projected is not None else None,
            }
        )
    most = max(clusters, key=lambda row: row.get('applied', 0), default=None) if clusters else None
    payload.update(
        {
            'clusters': clusters,
            'method': 'linear_regression' if ready else 'counts',
            'ready': ready,
            'ready_reason': '' if ready else f'Needs {MIN_YEARS} school-year snapshots to train Linear Regression.',
            'most_applied': (
                {'code': most['code'], 'name': most['name'], 'applied': most['applied']} if most else None
            ),
        }
    )
    return payload
