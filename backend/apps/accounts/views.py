from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import sessions
from apps.accounts.codes import RESEND_SECONDS
from apps.accounts.csrf import enforce_csrf
from apps.accounts.mail import account_ready_email
from apps.accounts.models import AuthSession
from apps.accounts.security_events import failed_sign_in
from apps.accounts.throttles import LoginAccountThrottle, ScopedThrottle
from apps.accounts.serializers import (
    ActivateAccountSerializer,
    AuthDenied,
    ChangePasswordSerializer,
    CodeCooldown,
    ForgotPasswordOtpSerializer,
    ForgotPasswordSerializer,
    ForgotPasswordVerifySerializer,
    LoginSerializer,
    PasswordCodeVerifySerializer,
    PasswordOtpSerializer,
    UserSerializer,
    send_password_otp,
)
from apps.audit import services as audit
from apps.accounts.models import User


def set_refresh_cookie(response, raw):
    """The refresh token goes only into this cookie: HttpOnly, scoped to /api/auth/, Secure outside development.

    It has no expiry date, so it ends when the browser closes; the server ends the session earlier on idle or on the
    hard limit (apps.accounts.sessions).
    """
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE,
        raw,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def signed_in_response(user, session, raw):
    """The answer to a completed sign-in or refresh: the access token and the user in the body, the refresh
    token only in the cookie."""
    response = Response({'access': sessions.access_token(session), 'user': UserSerializer(user).data})
    set_refresh_cookie(response, raw)
    return response


def complete_sign_in(user):
    """Every sign-in step has passed: open the session and answer with its tokens."""
    session, raw = sessions.start(user)
    audit.record(user=user, action='login', summary=f'{user.email} signed in', target_type='User', target_id=user.id)
    return signed_in_response(user, session, raw)


class CsrfTokenView(APIView):
    """Hands the frontend the CSRF token for login, refresh and logout (see apps.accounts.csrf)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'csrf_token': get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle, LoginAccountThrottle]
    throttle_scope = 'login'

    def post(self, request):
        enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except AuthDenied as exc:
            if exc.get_codes() == AuthDenied.default_code:
                failed_sign_in(request, request.data.get('identifier'))
            raise
        user = serializer.validated_data['user']
        return complete_sign_in(user)


class RefreshView(APIView):
    """Uses the refresh cookie once and sets the next one. Also restores the sign-in after a page reload."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'refresh'

    def post(self, request):
        enforce_csrf(request)
        try:
            session, raw = sessions.rotate(request.COOKIES.get(settings.AUTH_REFRESH_COOKIE, ''))
        except sessions.SessionConflict:
            return Response(
                {'detail': 'Another tab refreshed the sign-in a moment ago. Try again.', 'code': 'refresh_conflict'},
                status=status.HTTP_409_CONFLICT,
            )
        except sessions.SessionInvalid:
            response = Response(
                {'detail': 'Your sign-in has ended. Please sign in again.', 'code': 'session_ended'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response)
            return response
        return signed_in_response(session.user, session, raw)


class LogoutView(APIView):
    """Ends the session on the server and deletes the cookie. Works even after the access token expired."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        enforce_csrf(request)
        session = sessions.end_by_token(request.COOKIES.get(settings.AUTH_REFRESH_COOKIE, ''), AuthSession.EndReason.LOGOUT)
        if session is not None:
            audit.record(
                user=session.user,
                action='logout',
                summary=f'{session.user.email} signed out',
                target_type='User',
                target_id=session.user_id,
            )
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

    def post(self, request):
        serializer = ActivateAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['password'])
        user.account_status = User.AccountStatus.ACTIVE
        user.save(update_fields=['password', 'account_status'])
        sessions.end_all(user, AuthSession.EndReason.PASSWORD)
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
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

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
        return Response({'detail': 'A code was sent to your email.', 'resend_in': RESEND_SECONDS})


class PasswordCodeVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

    def post(self, request):
        serializer = PasswordCodeVerifySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'Code verified.', 'verified': True})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        current = sessions.session_for_access(request.auth, request.user) if request.auth else None
        ended = sessions.end_all(request.user, AuthSession.EndReason.PASSWORD, keep=current)
        audit.record(
            user=request.user,
            action='password_change',
            summary=f'{request.user.email} changed password',
            target_type='User',
            target_id=request.user.id,
            details={'other_sign_ins_ended': ended},
        )
        return Response({'detail': 'Password updated. Other devices were signed out.'})


class ForgotPasswordOtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

    def post(self, request):
        serializer = ForgotPasswordOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')
        # The answer is the same whether or not the account exists, or a code was just sent.
        if user is not None:
            try:
                send_password_otp(user)
            except CodeCooldown:
                pass
            else:
                audit.record(
                    user=user,
                    action='password_otp_requested',
                    summary=f'{user.email} requested a password reset code',
                    target_type='User',
                    target_id=user.id,
                )
        return Response({'detail': 'If that account exists, a code was sent.', 'resend_in': RESEND_SECONDS})


class ForgotPasswordVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

    def post(self, request):
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'Code verified.', 'verified': True})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'codes'

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        ended = sessions.end_all(user, AuthSession.EndReason.PASSWORD)
        audit.record(
            user=user,
            action='password_change',
            summary=f'{user.email} reset a forgotten password',
            target_type='User',
            target_id=user.id,
            details={'sign_ins_ended': ended},
        )
        return Response({'detail': 'Password updated. You can sign in now.'})
