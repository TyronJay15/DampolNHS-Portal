import statistics

from django.core.management.base import BaseCommand

from apps.grading.recommend import recommendation_grades
from apps.ml.features import transform
from apps.ml.knn_model import compare_all
from apps.ml.recommender import MIN_SKILLS, RecommenderContext
from apps.people.models import StudentSection


class Command(BaseCommand):
    help = (
        'Print the closest-program distance distribution for currently placed students, so academic '
        'tier cut-offs can be set from real matches. Reads only; writes nothing.'
    )

    def handle(self, *args, **options):
        context = RecommenderContext()
        student_ids = list(StudentSection.objects.filter(is_active=True).values_list('student_id', flat=True).distinct())
        grades = recommendation_grades(student_ids, released_only=False)
        best = []
        for student_id in student_ids:
            features = transform(grades[student_id], context.schema, context.domains)
            if features.observed_count < MIN_SKILLS:
                continue
            distances = [row.distance for row in compare_all(features, context.candidates) if row.eligible]
            if distances:
                best.append(min(distances))
        self.stdout.write(f'Closest-program distance for {len(best)} placed students (grade points, lower is closer)')
        if len(best) >= 2:
            quartiles = statistics.quantiles(best, n=4)
            self.stdout.write(
                f'  min {min(best):.2f} · 25% {quartiles[0]:.2f} · median {quartiles[1]:.2f} · '
                f'75% {quartiles[2]:.2f} · max {max(best):.2f}'
            )
        tiers = context.config['academic_tiers']
        self.stdout.write(f'  Active cut-offs: strong <= {tiers["strong"]}, moderate <= {tiers["moderate"]}')
