"""Send queued registration emails. The host runs it: an always-on task (--loop) or a cron job (once)."""

import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.accounts import outbox

PRUNE_EVERY = 3600  # seconds between clean-ups while looping


class Command(BaseCommand):
    help = 'Send queued registration emails within the daily budget, then remove old finished rows.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true', help='Keep running, for an always-on task.')
        parser.add_argument('--interval', type=int, default=10, help='Seconds between rounds with --loop.')
        parser.add_argument('--limit', type=int, default=100, help='Most emails per round.')
        parser.add_argument('--seconds', type=int, default=180, help='Longest a round may run.')

    def handle(self, *args, **options):
        if not options['loop']:
            self._round(options, prune=True)
            return
        self.stdout.write('Sending queued emails. Stop with Ctrl+C.')
        pruned_at = 0.0
        try:
            while True:
                close_old_connections()
                prune = time.monotonic() - pruned_at >= PRUNE_EVERY
                self._round(options, prune=prune, quiet=True)
                if prune:
                    pruned_at = time.monotonic()
                time.sleep(options['interval'])
        except KeyboardInterrupt:
            self.stdout.write('Stopped.')

    def _round(self, options, prune, quiet=False):
        result = outbox.run_once(limit=options['limit'], seconds=options['seconds'])
        removed = outbox.prune() if prune else 0
        if quiet and not (result['sent'] or result['retrying'] or result['failed'] or removed):
            return
        self.stdout.write(
            f'Sent {result["sent"]}, retrying {result["retrying"]}, failed {result["failed"]}, '
            f'waiting for tomorrow {result["waiting"]}. Removed {removed} old rows.'
        )
