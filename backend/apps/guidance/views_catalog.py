"""The active college program catalog, readable by every signed-in portal user."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.guidance.permissions import CanReadCatalog
from apps.guidance.serializers import family_payload, program_payload
from apps.ml.models import CollegeProgram, ProgramFamily


def catalog_queryset():
    return (
        CollegeProgram.objects.filter(is_active=True)
        .exclude(family__is_active=False)
        .select_related('family')
        .prefetch_related('skills__domain', 'shs_programs')
        .order_by('family__sort_order', 'name')
    )


class ProgramCatalogView(APIView):
    permission_classes = [CanReadCatalog]

    def get(self, request):
        rows = catalog_queryset()
        family = str(request.query_params.get('family') or '').strip()
        if family:
            rows = rows.filter(family__code=family)
        return Response(
            {
                'families': [family_payload(row) for row in ProgramFamily.objects.filter(is_active=True)],
                'programs': [program_payload(program) for program in rows],
            }
        )
