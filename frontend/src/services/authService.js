import { apiRequest, clearTokens, setTokens } from './api';

export async function login({ identifier, password, recaptcha_token }) {
  const data = await apiRequest('/auth/login/', {
    method: 'POST',
    body: { identifier, password, recaptcha_token },
  });
  setTokens({ access: data.access, refresh: data.refresh });
  return data.user;
}

export async function logout() {
  const refresh = localStorage.getItem('refreshToken');
  try {
    if (refresh) {
      await apiRequest('/auth/logout/', { method: 'POST', auth: true, body: { refresh } });
    }
  } catch {
    // Local sign-out still proceeds.
  }
  clearTokens();
}

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

export function changePassword({ current_password, new_password, confirm_password, code }) {
  return apiRequest('/auth/change-password/', {
    method: 'POST',
    auth: true,
    body: { current_password, new_password, confirm_password, code },
  });
}

export function requestPasswordOtpPublic({ identifier, current_password }) {
  return apiRequest('/auth/change-password-public/otp/', {
    method: 'POST',
    body: { identifier, current_password },
  });
}

export function changePasswordPublic(payload) {
  return apiRequest('/auth/change-password-public/', {
    method: 'POST',
    body: payload,
  });
}

export function requestForgotPasswordOtp({ identifier, recaptcha_token }) {
  return apiRequest('/auth/forgot-password/otp/', {
    method: 'POST',
    body: { identifier, recaptcha_token },
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
