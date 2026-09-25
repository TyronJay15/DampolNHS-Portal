from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.people.serializers import StudentRegisterSerializer


class StudentRegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = StudentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        audit.record(
            user=user,
            action='register',
            summary=f'Student registration submitted for {user.email}',
            target_type='User',
            target_id=user.id,
        )
        return Response(
            {
                'detail': 'Registration submitted. Wait for administrator approval before signing in.',
                'email': user.email,
                'approval_status': user.approval_status,
            },
            status=status.HTTP_201_CREATED,
        )
