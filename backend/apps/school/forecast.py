"""Grade 11 enrollment picture and next-year plan, read from the database.

Observed: this year's applications, approvals and section fill per Grade 11 cluster.
Estimated: next year's Grade 12 intake (this year's approved Grade 11 continuing).
The trend forecast for next year's Grade 11 intake is added by apps.ml.forecast.
"""

import math

from django.db.models import Count, Q

from apps.people.models import Registration
from apps.school.curriculum import curriculum_for, programs_for
from apps.school.models import SchoolYear, Section

GRADE_11 = 'Grade 11'
GRADE_12 = 'Grade 12'
DEFAULT_CAPACITY = Section._meta.get_field('capacity').default


def next_year_label(label):
    try:
        start, end = str(label).split('-')
        return f'{int(start) + 1}-{int(end) + 1}'
    except (TypeError, ValueError):
        return ''


def sections_needed(students, capacity):
    return math.ceil(students / capacity) if students and capacity else 0


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


def build_grade11_forecast(year=None):
    year = year or SchoolYear.objects.filter(is_current=True).first()
    if year is None:
        return {
            'school_year': '',
            'projected_year': '',
            'curriculum': None,
            'grade11_total': 0,
            'applied_total': 0,
            'typical_capacity': DEFAULT_CAPACITY,
            'clusters': [],
            'strands': [],
            'grade12_unmapped': [],
            'plan': {'grade12_curriculum': None, 'grade12_curriculum_set': False, 'warnings': []},
        }

    counts = enrollment_counts(year)
    programs = grade11_programs(year, counts)
    fill = section_fill(year, [program.pk for program in programs])
    capacities = [row['capacity'] for rows in fill.values() for row in rows if row['capacity']]
    typical = round(sum(capacities) / len(capacities)) if capacities else DEFAULT_CAPACITY
    applied_total = sum(row['applied'] for row in counts.values())

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
                'count': 0,
                'basis': 'estimated',
                'ready': bool(target) and item['grade12_curriculum'] == target.code,
            },
        )
        strand['count'] += item['count']
    for strand in strands.values():
        strand['sections_needed'] = sections_needed(strand['count'], typical)

    return {
        'school_year': year.label,
        'projected_year': next_year_label(year.label),
        'curriculum': {'code': curriculum.code, 'name': curriculum.name} if curriculum else None,
        'grade11_total': sum(item['count'] for item in clusters),
        'applied_total': applied_total,
        'typical_capacity': typical,
        'clusters': clusters,
        'strands': sorted(strands.values(), key=lambda item: (-item['count'], item['code'])),
        'grade12_unmapped': [item['code'] for item in clusters if not item['grade12_code']],
        'plan': {
            'grade12_curriculum': {'code': target.code, 'name': target.name} if target else None,
            'grade12_curriculum_set': configured,
            'warnings': _plan_warnings(clusters, target, configured, curriculum),
        },
    }
