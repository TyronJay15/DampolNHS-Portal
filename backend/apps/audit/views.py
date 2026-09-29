from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.audit.models import AuditLog


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        rows = AuditLog.objects.all()[:200]
        return Response(
            [
                {
                    'id': row.id,
                    'action': row.action,
                    'family': row.family,
                    'summary': row.summary,
                    'actor': row.actor_label,
                    'role': row.actor_role,
                    'target_type': row.target_type,
                    'target_id': row.target_id,
                    'details': row.details,
                    'created_at': row.created_at,
                }
                for row in rows
            ]
        )
