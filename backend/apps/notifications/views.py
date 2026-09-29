from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification


def _payload(row):
    return {
        'id': row.id,
        'title': row.title,
        'body': row.body,
        'level': row.level,
        'category': row.category,
        'action_path': row.action_path,
        'is_read': row.is_read,
        'created_at': row.created_at,
    }


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = list(Notification.objects.filter(user=request.user)[:50])
        return Response(
            {
                'notifications': [_payload(row) for row in rows],
                'unread': Notification.objects.filter(user=request.user, is_read=False).count(),
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        row = get_object_or_404(Notification, pk=pk, user=request.user)
        if not row.is_read:
            row.is_read = True
            row.save(update_fields=['is_read'])
        return Response(_payload(row))


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        marked = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'marked': marked})
