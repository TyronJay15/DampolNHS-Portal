"""Student endpoints. None takes a student id: each reads the signed-in student's own profile."""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.guidance import assessment, consent
from apps.guidance.permissions import IsGuidanceStudent
from apps.guidance.recommendations import current_run, program_fits, run_payload
from apps.guidance.selectors import active_instrument, latest_completed, open_attempt
from apps.guidance.serializers import program_payload
from apps.guidance.views_catalog import catalog_queryset

MAX_COMPARE = 3


def _student(request):
    return request.user.student_profile


def _overview(student):
    attempt = open_attempt(student)
    completed = latest_completed(student)
    instrument = active_instrument()
    return {
        'consent': consent.consent_state(student),
        'assessment': {
            'open': instrument is not None,
            'status': 'in_progress' if attempt else 'completed' if completed else 'not_started',
            'completed_at': completed.completed_at if completed else None,
            'questions': instrument.questions.filter(is_active=True).count() if instrument else 0,
        },
        'recommendation': run_payload(current_run(student)),
    }


class GuidanceOverviewView(APIView):
    permission_classes = [IsGuidanceStudent]

    def get(self, request):
        return Response(_overview(_student(request)))


class ConsentView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'

    def post(self, request):
        student = _student(request)
        consent.give(
            student,
            request.data.get('kind'),
            guardian_confirmed=request.data.get('guardian_confirmed') is True,
            notice_version=str(request.data.get('notice_version') or ''),
            user=request.user,
        )
        return Response(_overview(student))


class ConsentWithdrawView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'

    def post(self, request):
        student = _student(request)
        consent.withdraw(student, request.data.get('kind'), user=request.user)
        return Response(_overview(student))


class AssessmentView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'
    throttle_methods = ('DELETE',)

    def get(self, request):
        student = _student(request)
        instrument = active_instrument()
        attempt = open_attempt(student)
        return Response(
            {
                'instrument': (
                    {
                        'name': instrument.name,
                        'version': instrument.version,
                        'attribution': instrument.attribution,
                        'license_url': instrument.license_url,
                        'questions': [
                            {'id': row.pk, 'position': row.position, 'text': row.text}
                            for row in assessment.questions(instrument)
                        ],
                    }
                    if instrument
                    else None
                ),
                'attempt': assessment.progress(attempt),
                'completed_at': getattr(latest_completed(student), 'completed_at', None),
            }
        )

    def delete(self, request):
        """Delete my answers and saved recommendations; consent records stay as proof."""
        student = _student(request)
        consent.delete_data(student, user=request.user)
        return Response(_overview(student))


class AssessmentStartView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'

    def post(self, request):
        attempt = assessment.start(_student(request))
        return Response({'attempt': assessment.progress(attempt)})


class AssessmentAnswerView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_answer'

    def put(self, request):
        question = request.data.get('question')
        if isinstance(question, bool) or not isinstance(question, int):
            raise ValidationError({'question': 'Send the question id.'})
        attempt = assessment.answer(_student(request), question, request.data.get('value'))
        return Response({'attempt': assessment.progress(attempt)})


class AssessmentCompleteView(APIView):
    permission_classes = [IsGuidanceStudent]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'guidance_write'

    def post(self, request):
        student = _student(request)
        assessment.complete(student)
        return Response(_overview(student))


class ProgramFitView(APIView):
    """One program with how the student's own evidence relates to it."""

    permission_classes = [IsGuidanceStudent]

    def get(self, request, code):
        program = catalog_queryset().filter(code=code).first()
        if program is None:
            return Response({'detail': 'Program not found.'}, status=404)
        fit = program_fits(_student(request), [program.code])[program.code]
        return Response({'program': program_payload(program), 'fit': fit})


class CompareView(APIView):
    permission_classes = [IsGuidanceStudent]

    def get(self, request):
        codes = [code.strip() for code in str(request.query_params.get('programs') or '').split(',') if code.strip()]
        codes = list(dict.fromkeys(codes))
        if not 2 <= len(codes) <= MAX_COMPARE:
            raise ValidationError({'programs': 'Choose two or three programs to compare.'})
        programs = {program.code: program for program in catalog_queryset().filter(code__in=codes)}
        if len(programs) != len(codes):
            raise ValidationError({'programs': 'One or more of these programs is not available.'})
        fits = program_fits(_student(request), codes)
        return Response({'programs': [{'program': program_payload(programs[code]), 'fit': fits[code]} for code in codes]})
