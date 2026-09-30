from django.core.management.base import BaseCommand

from apps.ml.forecast import train_forecast


class Command(BaseCommand):
    help = 'Snapshot Grade 11 programs per school year and train the Linear Regression forecast.'

    def handle(self, *args, **options):
        run = train_forecast()
        evaluation = run.metrics.get('evaluation') or {}
        self.stdout.write(
            self.style.SUCCESS(
                f'Forecast v{run.version} trained. ready={run.metrics.get("ready")} '
                f'years={run.dataset.get("years")} snapshots={run.n_train} '
                f'evaluation={evaluation.get("rmse", evaluation.get("reason"))}'
            )
        )
