from apps.ml.models import ModelRun


def last_run(name):
    return ModelRun.objects.filter(name=name).first()


def last_artifact(name):
    run = last_run(name)
    return run.artifact if run else None


def save_run(*, name, algorithm, n_train, n_test, metrics, artifact):
    return ModelRun.objects.create(
        name=name,
        algorithm=algorithm,
        n_train=n_train,
        n_test=n_test,
        metrics=metrics,
        artifact=artifact,
    )
