from collections import Counter

from apps.people.models import Registration
from apps.school.models import SchoolYear
from apps.school.program_catalog import GRADE11_TO_GRADE12, catalog_item


def next_year_label(label):
    try:
        start, end = str(label).split('-')
        return f'{int(start) + 1}-{int(end) + 1}'
    except (TypeError, ValueError):
        return ''


def build_grade11_forecast(year=None):
    year = year or SchoolYear.objects.filter(is_current=True).first()
    if year is None:
        return {
            'school_year': '',
            'projected_year': '',
            'grade11_total': 0,
            'clusters': [],
            'strands': [],
        }

    counts = Counter(
        Registration.objects.filter(
            status=Registration.Status.APPROVED,
            school_year=year,
            grade_level_enrollment='Grade 11',
        ).values_list('program__code', flat=True)
    )

    clusters = []
    strand_counts = Counter()
    for cluster_code, strand_code in GRADE11_TO_GRADE12.items():
        count = counts.get(cluster_code, 0)
        cluster = catalog_item(cluster_code)
        strand = catalog_item(strand_code)
        clusters.append(
            {
                'code': cluster_code,
                'name': cluster.get('name', cluster_code),
                'count': count,
                'grade12_code': strand_code,
                'grade12_name': strand.get('name', strand_code),
            }
        )
        strand_counts[strand_code] += count

    strands = [
        {
            'code': code,
            'name': catalog_item(code).get('name', code),
            'count': strand_counts[code],
        }
        for code in ('STEM', 'ABM', 'HUMSS', 'ICT', 'HE')
    ]

    return {
        'school_year': year.label,
        'projected_year': next_year_label(year.label),
        'grade11_total': sum(item['count'] for item in clusters),
        'clusters': clusters,
        'strands': strands,
    }
