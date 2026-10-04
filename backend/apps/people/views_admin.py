import logging
from collections import Counter

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import outbox
from apps.accounts.lifecycle import HIDDEN
from apps.accounts.models import StudentProfile, User
from apps.access.permissions import filter_levels, reading_levels, role_or_tagged
from apps.accounts.permissions import IsAdmin
from apps.audit import services as audit
from apps.people.models import Registration
from apps.people.registrations import AlreadyReviewed, approve_registration, reject_registration
from apps.people.serializers import (
    RegistrationReviewSerializer,
    RejectRegistrationSerializer,
    StudentGenderSerializer,
)

logger = logging.getLogger('apps.people.admin')
REVIEW_REGISTRATIONS = 'review_registrations'


class RegistrationListView(APIView):
    """Admins see every list. A head teacher tagged to review registrations sees pending ones in their levels."""

    permission_classes = [IsAuthenticated, role_or_tagged(User.Role.ADMIN, REVIEW_REGISTRATIONS)]

    def get(self, request):
        if request.user.role != User.Role.ADMIN:
            return self._tagged_review(request)
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
        rows = list(queryset)
        context = {'email_states': outbox.registration_states([row.id for row in rows])}
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
                'results': RegistrationReviewSerializer(rows, many=True, context=context).data,
            }
        )

    def _tagged_review(self, request):
        levels = reading_levels(request.user, REVIEW_REGISTRATIONS)
        queryset = filter_levels(
            Registration.objects.select_related('user', 'user__student_profile', 'program', 'school_year')
            .filter(status=Registration.Status.PENDING)
            .exclude(user__account_status=User.AccountStatus.REMOVED),
            levels,
            'grade_level_enrollment',
        )
        rows = RegistrationReviewSerializer(queryset, many=True).data
        return Response(
            {
                'counts': {'pending': len(rows), 'approved': 0, 'archived': 0, 'rejected': 0},
                'status': 'pending',
                'results': rows,
            }
        )


class RegistrationApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        registration = get_object_or_404(Registration.objects.select_related('user'), pk=pk)
        try:
            return Response(approve_registration(registration, request.user))
        except AlreadyReviewed:
            return Response(
                {'detail': 'This registration has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RegistrationBulkApproveView(APIView):
    """Approve the registrations an admin was shown. Only the listed ids are touched."""

    permission_classes = [IsAuthenticated, IsAdmin]
    MAX_IDS = 200

    def post(self, request):
        ids = request.data.get('ids')
        if not isinstance(ids, list) or not ids or not all(isinstance(item, int) and not isinstance(item, bool) for item in ids):
            return Response({'detail': 'Send the list of registration ids to approve.'}, status=400)
        ids = list(dict.fromkeys(ids))
        if len(ids) > self.MAX_IDS:
            return Response({'detail': f'Approve at most {self.MAX_IDS} registrations at a time.'}, status=400)

        found = Registration.objects.select_related('user').in_bulk(ids)
        approved, skipped, failed = [], [], []
        for registration_id in ids:
            registration = found.get(registration_id)
            if registration is None:
                failed.append({'id': registration_id, 'detail': 'Registration not found.'})
                continue
            try:
                result = approve_registration(registration, request.user)
            except AlreadyReviewed:
                skipped.append({'id': registration_id, 'detail': 'Already reviewed.'})
            except Exception:
                logger.exception('Bulk approval failed for registration %s', registration_id)
                failed.append({'id': registration_id, 'detail': 'Could not approve this registration.'})
            else:
                approved.append({'id': registration_id, 'email_status': result['email_status']})
        if approved:
            audit.record(
                user=request.user,
                action='registrations_bulk_approved',
                summary=f'Approved {len(approved)} student registrations at once',
                target_type='Registration',
                details={'approved': len(approved), 'skipped': len(skipped), 'failed': len(failed)},
            )
        return Response(
            {
                'approved': approved,
                'skipped': skipped,
                'failed': failed,
                'emails': dict(Counter(item['email_status'] for item in approved)),
            }
        )


class RegistrationEmailView(APIView):
    """The Admin's email delivery strip: counts and today's allowance."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(outbox.summary())


class RegistrationEmailResendView(APIView):
    """Queue every failed registration email again."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        resent = outbox.resend_failed()
        if resent:
            audit.record(
                user=request.user,
                action='registration_emails_resent',
                summary=f'Queued {resent} failed registration email{"" if resent == 1 else "s"} again',
                target_type='MailOutbox',
                details={'emails': resent},
            )
        return Response({'resent': resent, **outbox.summary()})


class RegistrationRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        serializer = RejectRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = get_object_or_404(
            Registration.objects.select_related('user'),
            pk=pk,
        )
        try:
            payload = reject_registration(registration, request.user, serializer.validated_data['reason'])
        except AlreadyReviewed:
            return Response(
                {'detail': 'This registration has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload)


class AdminAccountArchiveView(APIView):
    """Admin-only archive desk for student and staff accounts."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        kind = (request.query_params.get('kind') or 'students').strip().lower()
        if kind == 'staff':
            rows = (
                User.objects.filter(
                    role__in=(User.Role.TEACHER, User.Role.HEAD_TEACHER, User.Role.ADMIN),
                    account_status__in=(User.AccountStatus.ARCHIVED, User.AccountStatus.SUSPENDED),
                )
                .order_by('-approval_updated_at', 'last_name', 'first_name')
            )
            return Response(
                [
                    {
                        'id': row.id,
                        'name': row.get_full_name() or row.email,
                        'email': row.email,
                        'role': row.role,
                        'account_status': row.account_status,
                        'archived_at': row.approval_updated_at,
                        'kind': 'staff',
                    }
                    for row in rows
                ]
            )

        archived_regs = (
            Registration.objects.select_related('user', 'user__student_profile', 'program', 'school_year')
            .filter(user__account_status__in=(User.AccountStatus.ARCHIVED, User.AccountStatus.SUSPENDED))
            .exclude(user__account_status=User.AccountStatus.REMOVED)
            .order_by('-user__approval_updated_at')
        )
        rejected_regs = (
            Registration.objects.select_related('user', 'user__student_profile', 'program', 'school_year')
            .filter(status=Registration.Status.REJECTED)
            .exclude(user__account_status__in=HIDDEN)
            .order_by('-reviewed_at')
        )
        seen = set()
        payload = []
        for row in list(archived_regs) + list(rejected_regs):
            if row.user_id in seen:
                continue
            seen.add(row.user_id)
            data = RegistrationReviewSerializer(row).data
            data['archive_kind'] = (
                'rejected' if row.status == Registration.Status.REJECTED else 'archived'
            )
            data['archived_at'] = row.user.approval_updated_at or row.reviewed_at
            payload.append(data)
        return Response(payload)


class StudentGenderView(APIView):
    """PATCH /api/admin/accounts/<user id>/gender/ — the admin's correction, e.g. before a DepEd report."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        profile = get_object_or_404(StudentProfile.objects.select_related('user'), user_id=pk)
        serializer = StudentGenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous, gender = profile.gender, serializer.validated_data['gender']
        if previous != gender:
            profile.gender = gender
            profile.save(update_fields=['gender', 'updated_at'])
            audit.record(
                user=request.user,
                action='student_gender_set',
                summary=f'Set gender for {profile.user.get_full_name()} to {profile.get_gender_display()}',
                target_type='StudentProfile',
                target_id=profile.id,
                details={'from': previous, 'to': gender},
            )
        return Response({'user_id': profile.user_id, 'gender': profile.gender})
