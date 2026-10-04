from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chatbot.models import FaqEntry
from apps.chatbot.seeds import seed_faqs
from apps.ml.intent import train_intent


class Command(BaseCommand):
    help = 'Seed the default chatbot FAQs and train the intent classifier.'

    @transaction.atomic
    def handle(self, *args, **options):
        created = seed_faqs()
        run = train_intent()
        count = FaqEntry.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'FAQs ready: {count} active ({created} added); intent model v{run.version} '
                f'trained on {run.n_train} samples and tested on {run.n_test} '
                f'(accuracy {run.metrics["accuracy"]:.1%}).'
            )
        )