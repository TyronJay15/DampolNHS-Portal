"""Read-only data-quality report. Run before and after importing a database.

Imports (loaddata, raw SQL copies) skip model save(), so they can bring in records
the portal itself would refuse. This lists them; it changes nothing.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F, Q

from apps.people.models import Registration
from apps.school.models import Section, Subject


class Command(BaseCommand):
    help = (
        'List registrations and sections whose grade level does not match their program, '
        'and subjects that college matching ignores without being marked as excluded.'
    )

    def handle(self, *args, **options):
        problems = []
        unmapped = (
            Subject.objects.filter(matching_excluded=False)
            .filter(Q(skill_domain__isnull=True) | Q(skill_domain__is_active=False))
            .annotate(grade_count=Count('grades'))
            .filter(Q(is_active=True) | Q(grade_count__gt=0))
            .order_by('code')
        )
        for row in unmapped:
            problems.append(
                f'Subject {row.code}: no active skill domain and not marked excluded, '
                f'so college matching ignores its {row.grade_count} grade(s)'
            )
        registrations = (
            Registration.objects.exclude(program__grade_level='')
            .exclude(grade_level_enrollment=F('program__grade_level'))
            .select_related('program', 'school_year')
        )
        for row in registrations:
            problems.append(
                f'Registration {row.pk} ({row.school_year.label}): {row.grade_level_enrollment} '
                f'but {row.program.code} is {row.program.grade_level}'
            )
        sections = (
            Section.objects.exclude(program__isnull=True)
            .exclude(program__grade_level='')
            .exclude(grade_level=F('program__grade_level'))
            .select_related('program', 'school_year')
        )
        for row in sections:
            problems.append(
                f'Section {row.name} ({row.school_year.label}): {row.grade_level} '
                f'but {row.program.code} is {row.program.grade_level}'
            )
        for line in problems:
            self.stdout.write(self.style.WARNING(line))
        if problems:
            raise CommandError(f'{len(problems)} record(s) need fixing.')
        self.stdout.write(self.style.SUCCESS('No grade/program mismatches or unmapped subjects found.'))
