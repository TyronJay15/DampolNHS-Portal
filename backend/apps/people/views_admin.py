import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mail import registration_result_email
from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.notifications.services import notify
from apps.people.models import Registration
from apps.people.serializers import RegistrationReviewSerializer, RejectRegistrationSerializer

logger = logging.getLogger('apps.people.admin')


class RegistrationListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        status_filter = (request.query_params.get('status') or 'pending').strip().lower()
        allowed = {choice.value for choice in Registration.Status} | {'archived'}
        queryset = Registration.objects.select_related(
            'user',
            'user__student_profile',
            'program',
            'school_year',
            'reviewed_by',
        ).exclude(user__account_status=User.AccountStatus.REMOVED)
        if status_filter == 'archived':
            queryset = queryset.filter(user__account_status__in=(User.AccountStatus.ARCHIVED, User.AccountStatus.SUSPENDED))
        elif status_filter == Registration.Status.APPROVED:
            queryset = queryset.filter(status=Registration.Status.APPROVED).exclude(user__account_status__in=HIDDEN)
        elif status_filter in {choice.value for choice in Registration.Status}:
            queryset = queryset.filter(status=status_filter)
        counts = {
            'pending': Registration.objects.filter(status=Registration.Status.PENDING).count(),
            'approved': Registration.objects.filter(
                status=Registration.Status.APPROVED,
            ).exclude(user__account_status__in=HIDDEN).count(),
            'archived': Registration.objects.filter(
                user__account_status__in=(User.AccountStatus.ARCHIVED, User.AccountStatus.SUSPENDED),
            ).count(),
            'rejected': Registration.objects.filter(status=Registration.Status.REJECTED).count(),
        }
        return Response(
            {
                'counts': counts,
                'status': status_filter if status_filter in allowed else 'all',
                'results': RegistrationReviewSerializer(queryset, many=True).data,
            }
        )


class RegistrationApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        registration = get_object_or_404(
            Registration.objects.select_related('user'),
            pk=pk,
        )
        if registration.status != Registration.Status.PENDING:
            return Response(
                {'detail': 'This registration has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            now = timezone.now()
            user = registration.user
            user.approval_status = User.ApprovalStatus.APPROVED
            user.account_status = User.AccountStatus.ACTIVE
            user.approval_note = ''
            user.approval_updated_at = now
            user.save(update_fields=['approval_status', 'account_status', 'approval_note', 'approval_updated_at'])
            registration.status = Registration.Status.APPROVED
            registration.rejection_reason = ''
            registration.reviewed_at = now
            registration.reviewed_by = request.user
            registration.save(update_fields=['status', 'rejection_reason', 'reviewed_at', 'reviewed_by'])
        audit.record(
            user=request.user,
            action='account_approved',
            summary=f'Approved student account {user.email}',
            target_type='User',
            target_id=user.id,
            details={'registration_id': registration.id, 'email': user.email},
        )
        notify(
            [user],
            title='Account approved',
            body='You can sign in now. The Head Teacher will place you in a section.',
        )
        email_sent = True
        try:
            registration_result_email(user, approved=True)
        except Exception:
            email_sent = False
            logger.exception('Approval email failed for %s', user.email)
        registration.refresh_from_db()
        payload = dict(RegistrationReviewSerializer(registration).data)
        payload['email_sent'] = email_sent
        return Response(payload)


class RegistrationRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        serializer = RejectRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = get_object_or_404(
            Registration.objects.select_related('user'),
            pk=pk,
        )
        if registration.status != Registration.Status.PENDING:
            return Response(
                {'detail': 'This registration has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = serializer.validated_data['reason']
        with transaction.atomic():
            now = timezone.now()
            user = registration.user
            user.approval_status = User.ApprovalStatus.REJECTED
            user.approval_note = reason[:255]
            user.approval_updated_at = now
            user.save(update_fields=['approval_status', 'approval_note', 'approval_updated_at'])
            registration.status = Registration.Status.REJECTED
            registration.rejection_reason = reason
            registration.reviewed_at = now
            registration.reviewed_by = request.user
            registration.save(update_fields=['status', 'rejection_reason', 'reviewed_at', 'reviewed_by'])
        audit.record(
            user=request.user,
            action='account_rejected',
            summary=f'Rejected student account {user.email}',
            target_type='User',
            target_id=user.id,
            details={'registration_id': registration.id, 'email': user.email, 'reason': reason},
        )
        email_sent = True
        try:
            registration_result_email(user, approved=False, reason=reason)
        except Exception:
            email_sent = False
            logger.exception('Rejection email failed for %s', user.email)
        registration.refresh_from_db()
        payload = dict(RegistrationReviewSerializer(registration).data)
        payload['email_sent'] = email_sent
        return Response(payload)
