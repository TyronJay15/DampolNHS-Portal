"""Measure the chatbot's relevance thresholds against the labeled questions in apps.chatbot.evaluation.

Read-only: it uses the active FAQs and the latest trained intent model, and changes nothing. Run it after the
FAQs change and the classifier is retrained:

    python manage.py evaluate_chatbot          accuracy of the current thresholds, and the cases they miss
    python manage.py evaluate_chatbot --sweep  the best threshold combinations of the grid
"""

from django.core.management.base import BaseCommand

from apps.chatbot.evaluation import DEFAULTS, evaluate, sweep


class Command(BaseCommand):
    help = 'Measure the chatbot relevance thresholds on the labeled evaluation questions.'

    def add_arguments(self, parser):
        parser.add_argument('--sweep', action='store_true', help='Try every threshold combination of the grid.')
        parser.add_argument('--top', type=int, default=10, help='How many combinations to list with --sweep.')

    def handle(self, *args, **options):
        result = evaluate()
        groups = ', '.join(f'{group} {value:.0%}' for group, value in sorted(result['groups'].items()))
        self.stdout.write(
            f'Current thresholds {DEFAULTS}: accuracy {result["accuracy"]:.1%} ({groups}), '
            f'wrong answers {result["wrong_answers"]}'
        )
        for question, accepted, got in result['failures']:
            self.stdout.write(f'  missed: {question!r} -> {got} (expected {" or ".join(accepted)})')
        if options['sweep']:
            self.stdout.write('Best combinations:')
            for wrong, accuracy, thresholds in sweep()[: options['top']]:
                self.stdout.write(f'  wrong answers {wrong}, accuracy {accuracy:.1%}  {thresholds}')
