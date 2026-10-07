"""Data for the expert rating form. Raters submit through the access-request flow, which the Admin approves."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import role_or_tagged
from apps.accounts.models import User
from apps.guidance.catalog import IMPORTANCE_LABELS, MIN_RATERS, importance_of, rating_round
from apps.ml.models import CollegeProgram, ProgramSkillRating
from apps.school.models import SkillDomain


class RatingFormView(APIView):
    """Programs to rate, the skill areas, and the rater's own ratings for each program's current round.

    Current profile numbers are left out on purpose, so each expert rates independently.
    """

    permission_classes = [role_or_tagged(User.Role.ADMIN, 'rate_programs')]

    def get(self, request):
        programs = list(CollegeProgram.objects.select_related('family').order_by('family__sort_order', 'name'))
        mine = {}
        for row in ProgramSkillRating.objects.filter(rater=request.user).select_related('domain'):
            mine.setdefault((row.college_program_id, row.round), []).append(
                {
                    'domain': row.domain.key,
                    'importance': importance_of(row.level),
                    'level': str(row.level),
                    'benchmark': str(row.benchmark) if row.benchmark is not None else None,
                }
            )
        return Response(
            {
                'min_raters': MIN_RATERS,
                'importance': [{'key': key, 'label': label} for key, label in IMPORTANCE_LABELS.items()],
                'domains': [{'key': row.key, 'label': row.label} for row in SkillDomain.objects.filter(is_active=True)],
                'programs': [
                    {
                        'code': program.code,
                        'name': program.name,
                        'family': program.family.name if program.family_id else '',
                        'description': program.description,
                        'source': program.source,
                        'source_url': program.source_url,
                        'round': rating_round(program),
                        'mine': mine.get((program.pk, rating_round(program)), []),
                    }
                    for program in programs
                ],
            }
        )
