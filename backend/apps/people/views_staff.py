from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttles import ScopedThrottle
from apps.accounts.codes import issue_code
from apps.accounts.mail import activation_email
from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.accounts.staff_activation import activation_figures
from apps.audit import services as audit
from apps.people.serializers import StaffCreateSerializer


def _send_activation(user):
    """Issue a fresh code and email it. Returns whether the email went out."""
    return activation_email(user, issue_code(user, 'activate'))


class StaffAccountView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'email_resend'
    throttle_methods = ('POST',)

    def get(self, request):
        rows = list(
            User.objects.filter(role__in=(User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.ADMIN))
            .exclude(account_status=User.AccountStatus.REMOVED)
            .order_by('role', 'last_name', 'first_name')
        )
        figures = activation_figures(rows)
        return Response(
            [
                {
                    'id': row.id,
                    'name': row.get_full_name() or row.email,
                    'email': row.email,
                    'role': row.role,
                    'account_status': row.account_status,
                    'activation': figures.get(row.id),
                }
                for row in rows
            ]
        )

    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        emailed = _send_activation(user)
        audit.record(
            user=request.user,
            action='staff_created',
            summary=f'Created {user.role} account {user.email}',
            target_type='User',
            target_id=user.id,
            details={'email': user.email, 'role': user.role},
        )
        return Response(
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.role,
                'account_status': user.account_status,
                'activation_emailed': emailed,
            },
            status=201,
        )


class StaffActivationResendView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'email_resend'

    def post(self, request, pk):
        user = get_object_or_404(
            User.objects.filter(role__in=(User.Role.TEACHER, User.Role.HEAD_TEACHER)),
            pk=pk,
        )
        if user.account_status != User.AccountStatus.PENDING_ACTIVATION:
            return Response({'detail': 'That account is already active.'}, status=400)
        emailed = _send_activation(user)
        audit.record(
            user=request.user,
            action='staff_activation_resent',
            summary=f'Resent activation email to {user.email}',
            target_type='User',
            target_id=user.id,
        )
        detail = 'Activation email sent again.' if emailed else 'A new code was made, but the email did not go out.'
        return Response({'detail': detail, 'email': user.email, 'activation_emailed': emailed})
