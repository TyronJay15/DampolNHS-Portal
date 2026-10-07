"""Read-only trace of the ML pipeline against the live database. Writes nothing.

--student shows every step behind the academic side of a recommendation: the grades read,
where each one went (a skill domain, excluded, unmapped), the fixed feature vector and its
observed mask, and the comparison with every active college program. Interest scores are
not part of this trace; manage.py recommender_readiness prints the distance distribution. No names
are printed.
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.grading.recommend import recommend_payload, recommendation_grades
from apps.ml.features import subject_domains, to_model_space, transform
from apps.ml.forecast import attach_attractiveness
from apps.ml.knn_model import compare_all, evidence_threshold
from apps.ml.recommender import MIN_SKILLS, RecommenderContext
from apps.people.models import StudentSection
from apps.school.curriculum import curriculum_for
from apps.school.forecast import build_grade11_forecast
from apps.school.models import ProgramSubject, SchoolYear


class Command(BaseCommand):
    help = 'Trace database data -> ML input -> result: --student <id> or --forecast.'

    def add_arguments(self, parser):
        parser.add_argument('--student', type=int, help='StudentProfile id')
        parser.add_argument('--staff', action='store_true', help='Use approved + released grades (adviser view).')
        parser.add_argument('--forecast', action='store_true')
        parser.add_argument('--year', help='School year label for --forecast, e.g. 2025-2026')

    def handle(self, *args, **options):
        if options['student']:
            report = self._student(options['student'], options['staff'])
        elif options['forecast']:
            report = self._forecast(options.get('year'))
        else:
            raise CommandError('Pass --student <id> or --forecast.')
        self.stdout.write(json.dumps(report, indent=2, default=str))

    def _student(self, pk, staff):
        profile = StudentProfile.objects.filter(pk=pk).first()
        if profile is None:
            raise CommandError(f'No student profile {pk}.')
        placement = (
            StudentSection.objects.filter(student=profile, is_active=True)
            .select_related('section__program__curriculum', 'school_year')
            .first()
        )
        section = placement.section if placement else None
        program = section.program if section and section.program_id else None
        year = placement.school_year if placement else SchoolYear.objects.filter(is_current=True).first()
        grades = recommendation_grades([profile.pk], released_only=not staff)[profile.pk]
        context = RecommenderContext()
        schema = context.schema
        features = transform(grades, schema, context.domains)
        student = to_model_space(features.values, features.observed)
        curriculum = curriculum_for(year, section.grade_level) if section else None
        offered = set(ProgramSubject.objects.filter(program=program).values_list('subject_id', flat=True)) if program else set()
        domains = subject_domains({grade.subject_id for grade in grades}, context.domains)
        strand_group = program.strand_group if program else ''
        program_code = program.code if program else ''
        result = recommend_payload(grades, context, program_code=program_code, strand_group=strand_group)
        ordered = sorted(
            compare_all(features, context.candidates, strand_group, program_code),
            key=lambda row: (not row.eligible, row.distance, row.candidate.name),
        )
        positions = {
            row.candidate.code: index
            for index, row in enumerate((row for row in ordered if row.eligible), start=1)
        }

        def place(grade):
            key, excluded = domains.get(grade.subject_id, (None, False))
            return 'excluded' if excluded else key if key in schema.keys else 'unmapped'

        return {
            'student': profile.pk,
            'school_year': year.label if year else None,
            'grade_level': section.grade_level if section else None,
            'program': program.code if program else None,
            'curriculum': curriculum.code if curriculum else None,
            'grades_view': 'adviser (approved + released)' if staff else 'student (released)',
            'grades': [
                {
                    'subject': grade.subject.code,
                    'term_id': grade.term_id,
                    'score': str(grade.score),
                    'counts_as': place(grade),
                    'in_program': grade.subject_id in offered,
                }
                for grade in grades
            ],
            'grades_read': len(grades),
            'grades_used': features.used,
            'invalid_grades': features.invalid,
            'excluded_subjects': list(features.excluded),
            'unmapped_subjects': list(features.unmapped),
            'feature_schema': {'version': schema.version, 'keys': list(schema.keys)},
            'values': [str(value) if value is not None else None for value in features.values],
            'observed': list(features.observed),
            'model_space': [round(value, 3) for value in student],
            'enough_data': features.observed_count >= MIN_SKILLS,
            'configuration': {
                'version': context.config_row.version if context.config_row else None,
                'academic_tiers': context.config['academic_tiers'],
            },
            'evidence_threshold': evidence_threshold(),
            'comparisons': [
                self._comparison(row, positions.get(row.candidate.code), features, student)
                for row in ordered
            ],
            'result': {
                'ready': result['ready'],
                'evidence': result['evidence'],
                'courses': [
                    (row['code'], row['label'], row['distance'], row['evidence']['status']) for row in result['courses']
                ],
                'needs': result['coverage']['needs'],
                'not_evaluated': result['coverage']['not_evaluated'],
            },
            'model': result['model'],
            'generated_at': timezone.now(),
        }

    @staticmethod
    def _comparison(row, position, features, student):
        """Every number behind one student-vs-program comparison."""
        candidate = row.candidate
        return {
            'code': candidate.code,
            'name': candidate.name,
            'ranking_position': position,
            'eligible': row.eligible,
            'evidence': row.evidence,
            'strand_context': row.strand_context,
            'relevant_domains': list(candidate.levels),
            'observed_relevant_domains': list(row.observed),
            'unobserved_relevant_domains': list(row.unobserved),
            'coverage': f'{len(row.observed)} / {row.total} = {100 * row.coverage:.2f}%',
            'distance': round(row.distance, 3),
            'imputed_share': round(row.imputed_share, 3),
            'benchmarks': {
                key: {
                    'benchmark': str(item.value),
                    'official': item.official,
                    'student': str(features.value(key)) if features.value(key) is not None else None,
                    'status': row.benchmark_status[key],
                }
                for key, item in candidate.benchmarks.items()
            },
            'by_domain': {
                key: {
                    'student_grade': str(features.value(key)) if seen else None,
                    'student_relative': round(left, 3) if seen else None,
                    'program_level': str(candidate.levels[key]) if key in candidate.levels else None,
                    'program_relative': round(right, 3) if key in candidate.levels else None,
                    'difference': round(left - right, 3),
                    'squared_gap': round((left - right) ** 2, 3),
                }
                for key, left, right, seen in zip(features.schema.keys, student, candidate.vector, features.observed)
                if seen or key in candidate.levels
            },
        }

    def _forecast(self, label):
        year = SchoolYear.objects.filter(label=label).first() if label else None
        if label and year is None:
            raise CommandError(f'No school year {label}.')
        payload = attach_attractiveness(build_grade11_forecast(year))
        return {
            'school_year': payload['school_year'],
            'curriculum': payload['curriculum'],
            'method': payload['method'],
            'ready_reason': payload['ready_reason'],
            'model': payload['model'],
            'clusters': [
                {key: row[key] for key in ('code', 'grade_level', 'curriculum', 'applied', 'count', 'projected', 'grade12_code')}
                for row in payload['clusters']
            ],
            'strands': payload['strands'],
            'grade12_unmapped': payload['grade12_unmapped'],
            'generated_at': timezone.now(),
        }
