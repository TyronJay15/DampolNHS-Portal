from django.conf import settings
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.ml.forecast import attach_attractiveness, retrain
from apps.school.forecast import build_grade11_forecast
from apps.school.models import SchoolYear


def planning_payload():
    """The Admin planning page: live counts, the Grade 12 estimate and the Grade 11 intake. Read-only."""
    payload = attach_attractiveness(build_grade11_forecast())
    payload['demo'] = settings.DEMO_MODE
    return payload


class Grade11ForecastView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'retrain'
    throttle_methods = ('POST',)

    def get(self, request):
        return Response(planning_payload())

    def post(self, request):
        """Retrain the forecast on demand (Admin button)."""
        retrain(request.user)
        return Response(planning_payload())


class RetentionSerializer(serializers.Serializer):
    retention_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)


class ForecastRetentionView(APIView):
    """Set the current school year's Grade 11 to Grade 12 retention rate, an assumption for the estimate."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request):
        year = SchoolYear.objects.filter(is_current=True).first()
        if year is None:
            return Response({'detail': 'Set a current school year first.'}, status=400)
        serializer = RetentionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before, after = year.retention_rate, serializer.validated_data['retention_rate']
        if before != after:
            year.retention_rate = after
            year.save(update_fields=['retention_rate'])
            audit.record(
                user=request.user,
                action='retention_rate_changed',
                summary=f'Set the {year.label} Grade 12 retention rate from {before}% to {after}%',
                target_type='SchoolYear',
                target_id=year.id,
                details={'before': str(before), 'after': str(after)},
            )
        return Response(planning_payload())
