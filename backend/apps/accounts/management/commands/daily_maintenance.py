"""Daily privacy and housekeeping clean-up. Run once a day by a Railway cron service (see README).

- Sign-in sessions that ended or expired more than SESSION_KEEP_DAYS ago are deleted with their token hashes.
- Chatbot questions older than CHAT_QUESTION_KEEP_DAYS lose their text; the date, topic and source stay for the
  question statistics.
- College recommendation answers and saved recommendations for graduates older than GUIDANCE_KEEP_DAYS are deleted.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts import sessions
from apps.guidance.retention import prune_guidance
from apps.ml.models import ChatQuestion


class Command(BaseCommand):
    help = 'Delete old sign-in sessions, blank old chatbot question text, and prune old guidance answers.'

    def handle(self, *args, **options):
        removed = sessions.purge(older_than_days=settings.SESSION_KEEP_DAYS)
        cutoff = timezone.now() - timedelta(days=settings.CHAT_QUESTION_KEEP_DAYS)
        blanked = ChatQuestion.objects.filter(created_at__lt=cutoff).exclude(question='').update(question='')
        guidance = prune_guidance()
        self.stdout.write(
            f'Removed {removed} old session record(s); blanked {blanked} old chatbot question(s); '
            f'pruned {guidance["assessments"]} guidance assessment row(s) and {guidance["recommendations"]} saved run(s).'
        )
