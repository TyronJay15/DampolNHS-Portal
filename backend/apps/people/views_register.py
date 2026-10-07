from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.outbox import queue_duplicate_registration_notice
from apps.accounts.throttles import ScopedThrottle
from apps.audit import services as audit
from apps.people.serializers import StudentRegisterSerializer, existing_owners

RECEIVED = (
    'Registration received. If it can be processed, the school will review it and email you. '
    'You can sign in once it is approved.'
)


class StudentRegisterView(APIView):
    """Public registration. A new registration and one that repeats an existing email or LRN get the same
    answer, so the form never reveals whether someone is enrolled; the existing account's owner is emailed."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'register'

    def post(self, request):
        serializer = StudentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        owners = data['existing_owners']
        if not owners:
            try:
                user = serializer.save()
            except IntegrityError:
                # Another registration with the same email was saved a moment ago.
                owners = existing_owners(data['email'], data['lrn'])
            else:
                audit.record(
                    user=user,
                    action='register',
                    summary=f'Student registration submitted for {user.email}',
                    target_type='User',
                    target_id=user.id,
                )
        if owners:
            self._repeat(owners, data['password'])
        return Response(
            {'detail': RECEIVED, 'email': data['email'], 'approval_status': 'pending'},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _repeat(owners, password):
        # Hash the password anyway, so the answer takes as long as a real registration.
        make_password(password)
        for owner in owners:
            queue_duplicate_registration_notice(owner)
            audit.record(
                user=None,
                action='register_duplicate',
                summary=f'A registration repeated the email or LRN of account #{owner.pk}; nothing was created',
                target_type='User',
                target_id=owner.pk,
            )
