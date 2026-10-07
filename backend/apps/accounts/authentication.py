"""Request authentication: a valid access token is not enough on its own.

Every request also needs the token's sign-in session to be open and the account to still be allowed to sign in, so
signing out, a password reset, deactivation or archiving takes effect immediately, not when the token expires.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.sessions import session_for_access


class PortalJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.can_sign_in:
            raise AuthenticationFailed('This account can no longer sign in.', code='account_unavailable')
        if session_for_access(validated_token, user) is None:
            raise AuthenticationFailed('Your sign-in has ended. Please sign in again.', code='session_ended')
        return user
