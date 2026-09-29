from django.core.management.base import BaseCommand

from apps.ml.forecast import train_forecast


class Command(BaseCommand):
    help = 'Snapshot Grade 11 clusters and train Linear Regression attractiveness.'

    def handle(self, *args, **options):
        run = train_forecast()
        self.stdout.write(
            self.style.SUCCESS(
                f'Forecast trained. ready={run.metrics.get("ready")} years={run.n_train}'
            )
        )
