from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.ml.forecast import attach_attractiveness, train_forecast
from apps.school.forecast import build_grade11_forecast


class Grade11ForecastView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(attach_attractiveness(build_grade11_forecast()))

    def post(self, request):
        """Retrain the forecast on demand (admin button)."""
        run = train_forecast()
        audit.record(
            user=request.user,
            action='model_trained',
            summary=f'Retrained the enrollment forecast (v{run.version})',
            target_type='ModelRun',
            target_id=run.id,
        )
        return Response(attach_attractiveness(build_grade11_forecast()))
