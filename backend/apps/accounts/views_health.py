import logging

from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('apps.accounts')


class HealthView(APIView):
    """Liveness only. Hosting uses this path and must not depend on MySQL being up."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'status': 'ok', 'service': 'dampol-nhs-portal'})


class ReadyView(APIView):
    """Readiness: the database answered. Does not report host names or the database error."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            logger.exception('Readiness check could not reach the database.')
            return Response({'status': 'not_ready'}, status=503)
        return Response({'status': 'ready'})
