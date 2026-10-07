import { apiRequest } from './api';

// Signing in, out and the sign-in session itself live in session.js; these are the account requests.
export { confirmMfaEnrollment, restore, signIn, signOut, startMfaEnrollment, verifyMfa } from './session';

export async function fetchMe() {
  return apiRequest('/auth/me/', { auth: true });
}

export async function registerStudent(payload) {
  return apiRequest('/register/', { method: 'POST', body: payload });
}

export function requestPasswordOtp({ current_password }) {
  return apiRequest('/auth/change-password/otp/', {
    method: 'POST',
    auth: true,
    body: { current_password },
  });
}

export function verifyPasswordOtp({ current_password, code }) {
  return apiRequest('/auth/change-password/verify/', {
    method: 'POST',
    auth: true,
    body: { current_password, code },
  });
}

export function changePassword({ current_password, new_password, confirm_password, code }) {
  return apiRequest('/auth/change-password/', {
    method: 'POST',
    auth: true,
    body: { current_password, new_password, confirm_password, code },
  });
}

export function requestForgotPasswordOtp({ identifier, recaptcha_token }) {
  return apiRequest('/auth/forgot-password/otp/', {
    method: 'POST',
    body: { identifier, recaptcha_token },
  });
}

export function verifyForgotPasswordOtp({ identifier, code, recaptcha_token }) {
  return apiRequest('/auth/forgot-password/verify/', {
    method: 'POST',
    body: { identifier, code, recaptcha_token },
  });
}

export function resetForgottenPassword(payload) {
  return apiRequest('/auth/forgot-password/', {
    method: 'POST',
    body: payload,
  });
}

export function activateAccount({ email, code, password, confirm_password }) {
  return apiRequest('/auth/activate/', {
    method: 'POST',
    body: { email, code, password, confirm_password },
  });
}

export function homePathForRole(role) {
  if (role === 'admin') return '/admin';
  if (role === 'head_teacher') return '/head';
  if (role === 'teacher') return '/teacher';
  return '/student';
}

// Authenticator app while signed in (Admin and Head Teacher). Changes need the password, and a code once set up.
export function fetchMfaStatus() {
  return apiRequest('/auth/mfa/', { auth: true });
}

export function startMfaSetup(password) {
  return apiRequest('/auth/mfa/enroll/', { method: 'POST', auth: true, body: { password } });
}

export function confirmMfaSetup(code) {
  return apiRequest('/auth/mfa/enroll/confirm/', { method: 'POST', auth: true, body: { code } });
}

export function renewRecoveryCodes({ password, code }) {
  return apiRequest('/auth/mfa/recovery-codes/', { method: 'POST', auth: true, body: { password, code } });
}

export function turnOffMfa({ password, code }) {
  return apiRequest('/auth/mfa/disable/', { method: 'POST', auth: true, body: { password, code } });
}
