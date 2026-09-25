from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.mail import account_ready_email
from apps.accounts.serializers import (
    ActivateAccountSerializer,
    ChangePasswordSerializer,
    ForgotPasswordOtpSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    PasswordOtpSerializer,
    PublicChangePasswordSerializer,
    PublicPasswordOtpSerializer,
    UserSerializer,
    send_password_otp,
)
from apps.audit import services as audit
from apps.accounts.models import User


def token_pair(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        audit.record(
            user=user,
            action='login',
            summary=f'{user.email} signed in',
            target_type='User',
            target_id=user.id,
        )
        return Response(token_pair(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('refresh')
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ActivateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['password'])
        user.account_status = User.AccountStatus.ACTIVE
        user.save(update_fields=['password', 'account_status'])
        account_ready_email(user)
        audit.record(
            user=user,
            action='staff_activated',
            summary=f'{user.email} activated a staff account',
            target_type='User',
            target_id=user.id,
        )
        return Response({'detail': 'Account activated. You can sign in now.'})


class PasswordOtpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordOtpSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        send_password_otp(serializer.validated_data['user'])
        audit.record(
            user=request.user,
            action='password_otp_requested',
            summary=f'{request.user.email} requested a password code',
            target_type='User',
            target_id=request.user.id,
        )
        return Response({'detail': 'A code was sent to your email.'})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        audit.record(
            user=request.user,
            action='password_change',
            summary=f'{request.user.email} changed password',
            target_type='User',
            target_id=request.user.id,
        )
        return Response({'detail': 'Password updated.'})


class ForgotPasswordOtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ForgotPasswordOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')
        if user is not None:
            send_password_otp(user)
            audit.record(
                user=user,
                action='password_otp_requested',
                summary=f'{user.email} requested a password reset code',
                target_type='User',
                target_id=user.id,
            )
        return Response({'detail': 'If that account exists, a code was sent.'})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        audit.record(
            user=user,
            action='password_change',
            summary=f'{user.email} reset a forgotten password',
            target_type='User',
            target_id=user.id,
        )
        return Response({'detail': 'Password updated. You can sign in now.'})


class PublicPasswordOtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PublicPasswordOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        send_password_otp(user)
        audit.record(
            user=user,
            action='password_otp_requested',
            summary=f'{user.email} requested a password code',
            target_type='User',
            target_id=user.id,
        )
        return Response({'detail': 'A code was sent to your email.'})


class PublicChangePasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PublicChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        audit.record(
            user=user,
            action='password_change',
            summary=f'{user.email} changed password',
            target_type='User',
            target_id=user.id,
        )
        return Response({'detail': 'Password updated.'})
