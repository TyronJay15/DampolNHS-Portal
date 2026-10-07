"""DEMO ONLY: add synthetic completed school years so the Grade 11 trend can be shown working.

It refuses to run unless DEMO_MODE is on (an explicit environment setting), so it can never write
invented history into the real school database. Every snapshot it writes is marked is_synthetic, and the
planning page shows "Synthetic demo data" whenever the trained model used one.

The timeline: two older years under the previous curriculum (kept, but excluded from training, to show
the curriculum boundary), then four completed years under the current Grade 11 curriculum, so the trend
unlocks and can be tested forward in time.
"""

import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.ml.forecast import train_forecast
from apps.ml.models import ClusterSnapshot
from apps.school.curriculum import curriculum_for, programs_for
from apps.school.forecast import GRADE_11
from apps.school.models import Curriculum, SchoolYear, SchoolYearCurriculum

OLD_YEARS = 2
NEW_YEARS = 4
SEED = 2026  # fixed, so the demo numbers are the same every time


def _label(start):
    return f'{start}-{start + 1}'


class Command(BaseCommand):
    help = 'DEMO ONLY (needs DEMO_MODE=true): add synthetic completed years and train the Grade 11 forecast.'

    def add_arguments(self, parser):
        parser.add_argument('--remove', action='store_true', help='Remove the synthetic years this command added.')

    def handle(self, *args, **options):
        if not getattr(settings, 'DEMO_MODE', False):
            raise CommandError('Refused: DEMO_MODE is off. Synthetic history may only be added to a demo database.')
        if options['remove']:
            self._remove()
            return
        current = SchoolYear.objects.filter(is_current=True).first()
        if current is None:
            raise CommandError('Set a current school year first.')
        curriculum = curriculum_for(current, GRADE_11)
        previous = Curriculum.objects.exclude(pk=getattr(curriculum, 'pk', None)).order_by('sort_order', 'code').first()
        programs = list(programs_for(current, GRADE_11))
        if curriculum is None or previous is None or not programs:
            raise CommandError('The current Grade 11 curriculum, an older curriculum and Grade 11 programs are needed.')

        start = int(current.label.split('-')[0])
        labels = [_label(start - offset) for offset in range(OLD_YEARS + NEW_YEARS, 0, -1)]
        taken = list(SchoolYear.objects.filter(label__in=labels).values_list('label', flat=True))
        if taken:
            raise CommandError(f'Refused: these years already exist and are not touched: {", ".join(taken)}.')

        rng = random.Random(SEED)
        shape = {program.pk: (rng.randint(18, 55), rng.uniform(-3, 6)) for program in programs}
        with transaction.atomic():
            for position, label in enumerate(labels):
                old = position < OLD_YEARS
                year = SchoolYear.objects.create(label=label, archived_at=timezone.now())
                year_curriculum = previous if old else curriculum
                SchoolYearCurriculum.objects.create(school_year=year, grade_level=GRADE_11, curriculum=year_curriculum)
                for program in programs:
                    base, slope = shape[program.pk]
                    applied = max(0, round(base + slope * position + rng.uniform(-4, 4)))
                    ClusterSnapshot.objects.create(
                        school_year=year,
                        cluster_code=program.code,
                        program=program,
                        curriculum=year_curriculum,
                        applied_count=applied,
                        approved_count=round(applied * rng.uniform(0.78, 0.92)),
                        is_synthetic=True,
                    )
        run = train_forecast()
        self.stdout.write(
            self.style.SUCCESS(
                f'Added synthetic years {labels[0]} to {labels[-1]} ({OLD_YEARS} under {previous.code}, '
                f'{NEW_YEARS} under {curriculum.code}). Forecast v{run.version} trained, ready={run.metrics["ready"]}.'
            )
        )

    def _remove(self):
        years = SchoolYear.objects.filter(cluster_snapshots__is_synthetic=True).distinct()
        labels = list(years.values_list('label', flat=True))
        with transaction.atomic():
            years.delete()
        run = train_forecast()
        self.stdout.write(self.style.SUCCESS(f'Removed synthetic years: {", ".join(labels) or "none"}. Forecast v{run.version} retrained.'))
