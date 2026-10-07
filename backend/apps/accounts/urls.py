from django.urls import path

from .views_mfa import (
    MfaDisableView,
    MfaEnrollConfirmView,
    MfaEnrollStartView,
    MfaRecoveryCodesView,
    MfaStatusView,
    MfaVerifyView,
)
from .views import (
    ActivateAccountView,
    ChangePasswordView,
    CsrfTokenView,
    ForgotPasswordOtpView,
    ForgotPasswordVerifyView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    PasswordCodeVerifyView,
    PasswordOtpView,
    RefreshView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('csrf/', CsrfTokenView.as_view(), name='auth-csrf'),
    path('refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('mfa/', MfaStatusView.as_view(), name='auth-mfa'),
    path('mfa/verify/', MfaVerifyView.as_view(), name='auth-mfa-verify'),
    path('mfa/enroll/', MfaEnrollStartView.as_view(), name='auth-mfa-enroll'),
    path('mfa/enroll/confirm/', MfaEnrollConfirmView.as_view(), name='auth-mfa-enroll-confirm'),
    path('mfa/recovery-codes/', MfaRecoveryCodesView.as_view(), name='auth-mfa-recovery-codes'),
    path('mfa/disable/', MfaDisableView.as_view(), name='auth-mfa-disable'),
    path('activate/', ActivateAccountView.as_view(), name='auth-activate'),
    path('change-password/otp/', PasswordOtpView.as_view(), name='auth-change-password-otp'),
    path('change-password/verify/', PasswordCodeVerifyView.as_view(), name='auth-change-password-verify'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('forgot-password/otp/', ForgotPasswordOtpView.as_view(), name='auth-forgot-password-otp'),
    path('forgot-password/verify/', ForgotPasswordVerifyView.as_view(), name='auth-forgot-password-verify'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
]
