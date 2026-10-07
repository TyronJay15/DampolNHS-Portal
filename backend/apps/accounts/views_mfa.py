"""Authenticator-app endpoints: the second sign-in step, set-up, recovery codes, turning it off, and the Admin's reset.

Signed-out calls (the second step and set-up during sign-in) carry the challenge from the password step and the
CSRF token, because the last one sets the sign-in cookie. Signed-in calls re-check the password.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import mfa, sessions
from apps.accounts.csrf import enforce_csrf
from apps.accounts.models import AuthSession, User
from apps.accounts.permissions import IsAdmin
from apps.accounts.security_events import mfa_failed
from apps.accounts.throttles import ScopedThrottle
from apps.accounts.views import complete_sign_in
from apps.audit import services as audit

CHALLENGE_EXPIRED = {'detail': 'This sign-in step expired. Sign in again.', 'code': 'challenge_invalid'}
WRONG_CODE = {'detail': 'That code is not correct. Check the app and try again.', 'code': 'mfa_invalid'}
WRONG_PASSWORD = {'detail': 'Your password is not correct.', 'code': 'password_invalid'}


def _wait_response(seconds):
    return Response(
        {'detail': f'Too many wrong codes. Try again in {seconds} seconds.', 'code': 'mfa_wait', 'retry_in': seconds},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def _record(user, action, summary, actor=None):
    audit.record(user=actor or user, action=action, summary=summary, target_type='User', target_id=user.pk)


class _SignedOutStep(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'mfa'


class MfaVerifyView(_SignedOutStep):
    """The second sign-in step: an authenticator code, or one recovery code."""

    def post(self, request):
        enforce_csrf(request)
        try:
            user = mfa.read_challenge(request.data.get('challenge'), mfa.VERIFY)
        except mfa.ChallengeInvalid:
            return Response(CHALLENGE_EXPIRED, status=status.HTTP_400_BAD_REQUEST)
        wait = mfa.wait_seconds(user)
        if wait:
            return _wait_response(wait)
        kind = mfa.verify_code(user, request.data.get('code'))
        if kind is None:
            mfa_failed(request, user)
            return Response(WRONG_CODE, status=status.HTTP_400_BAD_REQUEST)
        if kind == 'recovery':
            _record(user, 'mfa_recovery_used', f'Account #{user.pk} signed in with a recovery code')
        return complete_sign_in(user)


class MfaEnrollStartView(APIView):
    """Begin setting up the app: during a sign-in that requires it (challenge), or signed in (password)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        user, problem = _enrolling_user(request)
        if problem:
            return problem
        secret, uri, svg = mfa.start_enrollment(user)
        return Response({'secret': secret, 'otpauth_uri': uri, 'qr_svg': svg})


class MfaEnrollConfirmView(APIView):
    """Finish set-up with the first code from the app. Returns the recovery codes, shown this once."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        signed_in = request.user.is_authenticated
        user, problem = _enrolling_user(request, check_password=False)
        if problem:
            return problem
        codes = mfa.confirm_enrollment(user, request.data.get('code'))
        if codes is None:
            mfa_failed(request, user)
            return Response(WRONG_CODE, status=status.HTTP_400_BAD_REQUEST)
        _record(user, 'mfa_enrolled', f'Account #{user.pk} set up an authenticator app')
        if signed_in:
            return Response({'recovery_codes': codes})
        response = complete_sign_in(user)
        response.data['recovery_codes'] = codes
        return response


def _enrolling_user(request, check_password=True):
    """(user, None) or (None, error response). Signed in: the password is checked when starting. Signed out: the
    challenge from a sign-in that requires set-up, with the CSRF token."""
    if request.user.is_authenticated:
        if check_password and not request.user.check_password(str(request.data.get('password') or '')):
            return None, Response(WRONG_PASSWORD, status=status.HTTP_400_BAD_REQUEST)
        return request.user, None
    enforce_csrf(request)
    try:
        return mfa.read_challenge(request.data.get('challenge'), mfa.ENROLL), None
    except mfa.ChallengeInvalid:
        return None, Response(CHALLENGE_EXPIRED, status=status.HTTP_400_BAD_REQUEST)


class MfaStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                'enrolled': mfa.device_for(user) is not None,
                'required': mfa.required_for(user),
                'eligible': user.role in (User.Role.ADMIN, User.Role.HEAD_TEACHER),
                'recovery_codes_left': mfa.recovery_codes_left(user),
            }
        )


class _ConfirmedChange(APIView):
    """Changes to an existing set-up need the password and a current code."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedThrottle]
    throttle_scope = 'mfa'

    def check(self, request):
        user = request.user
        if not user.check_password(str(request.data.get('password') or '')):
            return Response(WRONG_PASSWORD, status=status.HTTP_400_BAD_REQUEST)
        wait = mfa.wait_seconds(user)
        if wait:
            return _wait_response(wait)
        if mfa.verify_code(user, request.data.get('code')) is None:
            mfa_failed(request, user)
            return Response(WRONG_CODE, status=status.HTTP_400_BAD_REQUEST)
        return None


class MfaRecoveryCodesView(_ConfirmedChange):
    def post(self, request):
        problem = self.check(request)
        if problem:
            return problem
        codes = mfa.new_recovery_codes(request.user)
        _record(request.user, 'mfa_recovery_codes_renewed', f'Account #{request.user.pk} made new recovery codes')
        return Response({'recovery_codes': codes})


class MfaDisableView(_ConfirmedChange):
    def post(self, request):
        problem = self.check(request)
        if problem:
            return problem
        mfa.remove(request.user)
        _record(request.user, 'mfa_disabled', f'Account #{request.user.pk} turned off the authenticator app')
        return Response({'enrolled': False, 'required': mfa.required_for(request.user)})


class AdminMfaResetView(APIView):
    """Admin: remove another person's authenticator after a lost phone. They set it up again at their next sign-in.
    Their sign-ins are ended. An Admin cannot reset their own (that is the server command's job)."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return Response({'detail': 'Another administrator must reset your authenticator.'}, status=400)
        mfa.remove(user)
        ended = sessions.end_all(user, AuthSession.EndReason.ADMIN)
        audit.record(
            user=request.user,
            action='mfa_reset',
            summary=f'Reset the authenticator app of account #{user.pk}',
            target_type='User',
            target_id=user.pk,
            details={'sign_ins_ended': ended},
        )
        return Response({'id': user.pk, 'enrolled': False})
