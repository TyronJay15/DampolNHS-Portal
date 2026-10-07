"""Admin endpoints for the college catalog, profiles, assessment, outcomes and settings."""

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.guidance import adviser, catalog, recommender_admin
from apps.guidance.models import InterestInstrument
from apps.guidance.permissions import IsGuidanceAdmin
from apps.guidance.serializers import family_payload, instrument_payload, program_payload
from apps.ml.models import (
    CollegeOutcome,
    CollegeProgram,
    FamilyInterestMap,
    ProgramFamily,
    ProgramProfileSnapshot,
    RecommenderConfig,
)
from apps.school.models import SkillDomain


def _programs():
    return CollegeProgram.objects.select_related('family', 'verified_by').prefetch_related('skills__domain', 'shs_programs')


def _families():
    types = {}
    for row in FamilyInterestMap.objects.order_by('riasec'):
        types.setdefault(row.family_id, []).append(row.riasec)
    return [
        {**family_payload(family, interest_types=types.get(family.pk, [])), 'programs': family.program_count}
        for family in ProgramFamily.objects.annotate(program_count=Count('programs')).order_by('sort_order', 'name')
    ]


class CatalogView(APIView):
    """Families and every program, active or not."""

    permission_classes = [IsGuidanceAdmin]

    def get(self, request):
        return Response(
            {
                'families': _families(),
                'programs': [program_payload(program, admin=True) for program in _programs().order_by('sort_order', 'code')],
            }
        )


class FamilyCreateView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def post(self, request):
        catalog.save_family(request.data, user=request.user)
        return Response({'families': _families()}, status=201)


class FamilyDetailView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def patch(self, request, code):
        family = get_object_or_404(ProgramFamily, code=code)
        catalog.save_family(request.data, user=request.user, family=family)
        return Response({'families': _families()})


class InterestMapView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def put(self, request):
        catalog.save_interest_map(request.data.get('map'), user=request.user)
        return Response({'families': _families()})


class ProgramCreateView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def post(self, request):
        program = catalog.create_program(request.data, user=request.user)
        return Response({'program': program_payload(_programs().get(pk=program.pk), admin=True)}, status=201)


def _program_detail(code):
    program = get_object_or_404(_programs(), code=code)
    return {
        'program': program_payload(program, admin=True),
        'ratings': catalog.rating_summary(program),
        'snapshots': [
            {
                'version': row.version,
                'status': row.status,
                'source': row.source,
                'note': row.note,
                'raters': len(row.validators),
                'created_at': row.created_at,
            }
            for row in ProgramProfileSnapshot.objects.filter(college_program=program).order_by('-version')
        ],
        'domains': [{'key': row.key, 'label': row.label} for row in SkillDomain.objects.filter(is_active=True)],
    }


class ProgramDetailView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def get(self, request, code):
        return Response(_program_detail(code))

    def patch(self, request, code):
        program = get_object_or_404(_programs(), code=code)
        catalog.update_program(program, request.data, user=request.user)
        return Response(_program_detail(code))


class ProgramActionView(APIView):
    """POST actions on one program: verify, requirement, apply-ratings."""

    permission_classes = [IsGuidanceAdmin]

    def post(self, request, code, action):
        program = get_object_or_404(_programs(), code=code)
        if action == 'verify':
            catalog.verify_program(program, request.data, user=request.user)
        elif action == 'requirement':
            catalog.set_official_requirement(program, request.data, user=request.user)
        elif action == 'apply-ratings':
            catalog.apply_ratings(program, user=request.user, source=request.data.get('source'), note=str(request.data.get('note') or ''))
        else:
            return Response({'detail': 'Unknown action.'}, status=404)
        return Response(_program_detail(code))


class CatalogImportView(APIView):
    permission_classes = [IsGuidanceAdmin]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'catalog_import'

    def post(self, request):
        commit = str(request.data.get('commit') or '').lower() == 'true'
        result = catalog.import_programs(request.FILES.get('file'), user=request.user, commit=commit)
        return Response(result)


class InstrumentListView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def get(self, request):
        return Response(
            {'instruments': [instrument_payload(row, with_questions=True) for row in InterestInstrument.objects.all()]}
        )


class InstrumentActivateView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def post(self, request, pk):
        instrument = get_object_or_404(InterestInstrument, pk=pk)
        catalog.activate_instrument(instrument, user=request.user, license_confirmed=request.data.get('license_confirmed'))
        return Response(
            {'instruments': [instrument_payload(row, with_questions=True) for row in InterestInstrument.objects.all()]}
        )


class OutcomeListView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def get(self, request):
        status = request.query_params.get('status') or CollegeOutcome.Status.RECORDED
        rows = (
            CollegeOutcome.objects.filter(status=status)
            .select_related('college_program', 'school_year', 'recorded_by', 'student__user')
            .order_by('-recorded_at')[:200]
        )
        return Response(
            {
                'outcomes': [
                    {
                        'id': row.pk,
                        'student': row.student.user.get_full_name(),
                        'program': row.college_program.name,
                        'school_year': row.school_year.label,
                        'status': row.status,
                        'recorded_by': row.recorded_by.get_full_name() if row.recorded_by else '',
                        'recorded_at': row.recorded_at,
                        'can_validate': row.recorded_by_id != request.user.pk,
                    }
                    for row in rows
                ]
            }
        )


class OutcomeValidateView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def post(self, request, pk):
        outcome = get_object_or_404(
            CollegeOutcome.objects.select_related('college_program__family', 'student'),
            pk=pk,
        )
        adviser.validate_outcome(outcome, user=request.user)
        return Response({'id': outcome.pk, 'status': outcome.status})


class RecommenderStatusView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def get(self, request):
        return Response(recommender_admin.status_payload())


class ConfigView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def get(self, request):
        return Response(recommender_admin.config_versions())

    def post(self, request):
        recommender_admin.save_config(
            request.data.get('values'),
            user=request.user,
            note=str(request.data.get('note') or ''),
            approved=request.data.get('approved') is True,
            activate=request.data.get('activate') is True,
        )
        return Response(recommender_admin.config_versions(), status=201)


class ConfigActivateView(APIView):
    permission_classes = [IsGuidanceAdmin]

    def post(self, request, pk):
        recommender_admin.activate_config(get_object_or_404(RecommenderConfig, pk=pk), user=request.user)
        return Response(recommender_admin.config_versions())
