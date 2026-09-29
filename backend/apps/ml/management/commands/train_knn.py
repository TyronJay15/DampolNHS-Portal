from django.core.management.base import BaseCommand

from apps.ml.knn_model import train_knn


class Command(BaseCommand):
    help = 'Train college KNN and choose k by cross-validation.'

    def handle(self, *args, **options):
        run = train_knn()
        self.stdout.write(
            self.style.SUCCESS(f'KNN trained. k={run.metrics.get("k")} n_train={run.n_train}')
        )
