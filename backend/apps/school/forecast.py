"""Grade 11 enrollment picture and next-year plan, read from the database. No model is involved here.

Observed (live data): this year's valid applications, approvals, approval rates, weekly registrations and
section fill per Grade 11 program. Valid means not rejected, the same rule the Admin's counts use.
Estimated: next year's Grade 12 intake, i.e. this year's approved Grade 11 students times the school year's
retention rate, followed through each program's "Leads to". The trend forecast for next year's Grade 11
intake is added by apps.ml.forecast.
"""

import math
from collections import Counter
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q
from django.utils import timezone

from apps.people.models import Registration
from apps.school.curriculum import curriculum_for, programs_for
from apps.school.models import SchoolYear, Section

GRADE_11 = 'Grade 11'
GRADE_12 = 'Grade 12'
DEFAULT_CAPACITY = Section._meta.get_field('capacity').default
DEFAULT_RETENTION = SchoolYear._meta.get_field('retention_rate').default


def next_year_label(label):
    try:
        start, end = str(label).split('-')
        return f'{int(start) + 1}-{int(end) + 1}'
    except (TypeError, ValueError):
        return ''


def sections_needed(students, capacity):
    return math.ceil(students / capacity) if students and capacity else 0


def rate(part, whole):
    """Percentage with one decimal, or None when there is nothing to divide."""
    return round(100 * part / whole, 1) if whole else None


def expected_students(approved, retention_rate):
    """Approved Grade 11 students expected to continue, rounded to whole students."""
    exact = Decimal(approved) * Decimal(retention_rate) / Decimal(100)
    return int(exact.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _valid(year, grade_level):
    return Registration.objects.filter(school_year=year, grade_level_enrollment=grade_level).exclude(
        status=Registration.Status.REJECTED
    )


def enrollment_counts(year, grade_level=GRADE_11):
    """The one aggregation of registrations per program: applied (not rejected) and approved."""
    rows = (
        Registration.objects.filter(school_year=year, grade_level_enrollment=grade_level)
        .values('program_id')
        .annotate(
            applied=Count('id', filter=~Q(status=Registration.Status.REJECTED)),
            approved=Count('id', filter=Q(status=Registration.Status.APPROVED)),
        )
    )
    return {row['program_id']: {'applied': row['applied'], 'approved': row['approved']} for row in rows}


def weekly_registrations(year, grade_level=GRADE_11):
    """Valid applications per week (weeks start on Monday) with the running total. Empty weeks are kept."""
    stamps = _valid(year, grade_level).exclude(submitted_at__isnull=True).values_list('submitted_at', flat=True)
    weeks = Counter()
    for stamp in stamps:
        day = timezone.localtime(stamp).date()
        weeks[day - timedelta(days=day.weekday())] += 1
    rows, total = [], 0
    week, last = (min(weeks), max(weeks)) if weeks else (None, None)
    while week is not None and week <= last:
        total += weeks[week]
        rows.append({'week_start': week.isoformat(), 'added': weeks[week], 'total': total})
        week += timedelta(days=7)
    return rows


def grade11_programs(year, counts):
    """Grade 11 programs offered that year, plus any program that holds registrations for it."""
    holding = [pk for pk, row in counts.items() if row['applied'] or row['approved']]
    return list(programs_for(year, GRADE_11, include_ids=holding))


def section_fill(year, program_ids):
    """Active sections per program with how many students are placed in each."""
    rows = (
        Section.objects.filter(school_year=year, program_id__in=program_ids, archived_at__isnull=True)
        .annotate(placed=Count('student_assignments', filter=Q(student_assignments__is_active=True)))
        .order_by('name')
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row.program_id, []).append(
            {'id': row.id, 'name': row.name, 'placed': row.placed, 'capacity': row.capacity}
        )
    return grouped


def planned_grade12_curriculum(year):
    """Next year's Grade 12 curriculum: as set for that year, else full implementation of Grade 11's."""
    next_year = SchoolYear.objects.filter(label=next_year_label(year.label)).first()
    configured = curriculum_for(next_year, GRADE_12) if next_year else None
    return configured or curriculum_for(year, GRADE_11), configured is not None


def _plan_warnings(clusters, target, configured, grade11_curriculum):
    warnings = []
    for row in clusters:
        if row['grade_level'] and row['grade_level'] != GRADE_11:
            warnings.append(f'{row["code"]} holds Grade 11 registrations but is a {row["grade_level"]} program.')
        elif not row['grade12_code']:
            warnings.append(f'{row["code"]} has no Grade 12 program set under "Leads to".')
        elif target and row['grade12_curriculum'] != target.code:
            warnings.append(f'{row["code"]} leads to {row["grade12_code"]}, which is not a {target.name} program.')
    if configured and grade11_curriculum and target != grade11_curriculum:
        warnings.append(f'Next year\'s Grade 12 is set to {target.name}. Change it on the School year page for full implementation.')
    return warnings


def _selection(year):
    """KDD selection and preprocessing counts for this year's records."""
    rows = Registration.objects.filter(school_year=year, grade_level_enrollment__in=(GRADE_11, GRADE_12))
    grade11 = rows.filter(grade_level_enrollment=GRADE_11)
    return {
        'records_read': rows.count(),
        'grade11_records': grade11.count(),
        'rejected_excluded': grade11.filter(status=Registration.Status.REJECTED).count(),
        'missing_timestamp': grade11.filter(submitted_at__isnull=True).count(),
    }


def build_grade11_forecast(year=None):
    year = year or SchoolYear.objects.filter(is_current=True).first()
    if year is None:
        return {
            'school_year': '',
            'projected_year': '',
            'curriculum': None,
            'grade11_total': 0,
            'applied_total': 0,
            'approval_rate': None,
            'retention_rate': str(DEFAULT_RETENTION),
            'typical_capacity': DEFAULT_CAPACITY,
            'clusters': [],
            'strands': [],
            'weekly': [],
            'grade12_expected_total': 0,
            'grade12_sections_next_year': 0,
            'grade12_unmapped': [],
            'selection': {},
            'plan': {'grade12_curriculum': None, 'grade12_curriculum_set': False, 'warnings': []},
        }

    counts = enrollment_counts(year)
    programs = grade11_programs(year, counts)
    fill = section_fill(year, [program.pk for program in programs])
    capacities = [row['capacity'] for rows in fill.values() for row in rows if row['capacity']]
    typical = round(sum(capacities) / len(capacities)) if capacities else DEFAULT_CAPACITY
    applied_total = sum(row['applied'] for row in counts.values())
    approved_total = sum(row['approved'] for row in counts.values())

    clusters = []
    for program in programs:
        row = counts.get(program.pk, {'applied': 0, 'approved': 0})
        sections = fill.get(program.pk, [])
        target = program.continues_to
        clusters.append(
            {
                'program_id': program.pk,
                'code': program.code,
                'name': program.name,
                'curriculum': program.curriculum.code if program.curriculum_id else '',
                'grade_level': program.grade_level,
                'applied': row['applied'],
                'count': row['approved'],
                'approval_rate': rate(row['approved'], row['applied']),
                'share': round(100 * row['applied'] / applied_total) if applied_total else 0,
                'basis': 'observed',
                'placed': sum(item['placed'] for item in sections),
                'capacity': sum(item['capacity'] for item in sections),
                'sections': sections,
                'grade12_code': target.code if target else '',
                'grade12_name': target.name if target else '',
                'grade12_curriculum': target.curriculum.code if target and target.curriculum_id else '',
            }
        )
    ranked = sorted(clusters, key=lambda item: (-item['applied'], item['code']))
    for position, item in enumerate(ranked, start=1):
        item['rank'] = position

    curriculum = curriculum_for(year, GRADE_11)
    target, configured = planned_grade12_curriculum(year)
    retention = year.retention_rate
    strands = {}
    for item in clusters:
        if not item['grade12_code']:
            continue
        strand = strands.setdefault(
            item['grade12_code'],
            {
                'code': item['grade12_code'],
                'name': item['grade12_name'],
                'curriculum': item['grade12_curriculum'],
                'from_codes': [],
                'count': 0,
                'basis': 'estimated',
                'ready': bool(target) and item['grade12_curriculum'] == target.code,
            },
        )
        strand['from_codes'].append(item['code'])
        strand['count'] += item['count']
    for strand in strands.values():
        strand['expected'] = expected_students(strand['count'], retention)
        strand['sections_needed'] = sections_needed(strand['expected'], typical)

    return {
        'school_year': year.label,
        'projected_year': next_year_label(year.label),
        'curriculum': {'code': curriculum.code, 'name': curriculum.name} if curriculum else None,
        'grade11_total': approved_total,
        'applied_total': applied_total,
        'approval_rate': rate(approved_total, applied_total),
        'retention_rate': str(retention),
        'typical_capacity': typical,
        'clusters': clusters,
        'strands': sorted(strands.values(), key=lambda item: (-item['count'], item['code'])),
        'weekly': weekly_registrations(year),
        'grade12_expected_total': sum(strand['expected'] for strand in strands.values()),
        'grade12_sections_next_year': sum(strand['sections_needed'] for strand in strands.values()),
        'grade12_unmapped': [item['code'] for item in clusters if not item['grade12_code']],
        'selection': _selection(year),
        'plan': {
            'grade12_curriculum': {'code': target.code, 'name': target.name} if target else None,
            'grade12_curriculum_set': configured,
            'warnings': _plan_warnings(clusters, target, configured, curriculum),
        },
    }
