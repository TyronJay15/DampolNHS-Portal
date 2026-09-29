from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.lifecycle import anonymize_account, deactivate_account, reactivate_account, restore_rejected_to_pending
from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin


class AccountDeactivateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        result = deactivate_account(request.user, user, request.data.get('reason', ''))
        user.refresh_from_db()
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'account_status': user.account_status,
                **result,
            }
        )


class AccountRemoveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        anonymize_account(request.user, user)
        user.refresh_from_db()
        return Response({'id': user.id, 'account_status': user.account_status})


class AccountReactivateView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        result = reactivate_account(request.user, user)
        user.refresh_from_db()
        return Response(
            {
                'id': user.id,
                'email': result['email'],
                'account_status': result['account_status'],
                'activation_sent': result['activation_sent'],
            }
        )


class AccountRestorePendingView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
        result = restore_rejected_to_pending(request.user, user)
        user.refresh_from_db()
        return Response(
            {
                'id': user.id,
                'email': result['email'],
                'approval_status': user.approval_status,
                'registration_id': result['registration_id'],
                'status': result['status'],
            }
        )
