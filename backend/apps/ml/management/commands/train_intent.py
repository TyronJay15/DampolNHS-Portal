from django.core.management.base import BaseCommand

from apps.ml.intent import train_intent


class Command(BaseCommand):
    help = 'Train the school-question intent classifier.'

    def handle(self, *args, **options):
        run = train_intent()
        self.stdout.write(
            self.style.SUCCESS(
                f'Intent trained. accuracy={run.metrics.get("accuracy")} n_train={run.n_train}'
            )
        )
