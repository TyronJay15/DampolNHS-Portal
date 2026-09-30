from django.db.models import Max

from apps.ml.models import ModelRun

KEEP_RUNS = 10


def last_run(name):
    return ModelRun.objects.filter(name=name).first()


def last_artifact(name):
    run = last_run(name)
    return run.artifact if run else None


def save_run(*, name, algorithm, n_train, n_test, metrics, artifact, feature_schema=None, curriculum_scope=None, dataset=None):
    latest = ModelRun.objects.filter(name=name).aggregate(version=Max('version'))['version'] or 0
    run = ModelRun.objects.create(
        name=name,
        algorithm=algorithm,
        version=latest + 1,
        n_train=n_train,
        n_test=n_test,
        metrics=metrics,
        artifact=artifact,
        feature_schema=feature_schema or {},
        curriculum_scope=curriculum_scope or [],
        dataset=dataset or {},
    )
    prune_runs(name)
    return run


def prune_runs(name, keep=KEEP_RUNS):
    """Keep the newest runs of one model; older ones only fill the table."""
    older = list(ModelRun.objects.filter(name=name).order_by('-trained_at', '-id').values_list('id', flat=True)[keep:])
    if older:
        ModelRun.objects.filter(id__in=older).delete()
